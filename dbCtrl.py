import json
import os
import django
import csv

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tour_recommendation.settings')
django.setup()

import pandas as pd
import numpy as np
from django.contrib.auth import get_user_model
from accounts.models import User
from recommend.models import Travel, Consume, Visit, PopularTour, Recommendation # 모델을 가져옵니다.
from chatbot.models import TouristSpot
from collections import Counter
from django.db import transaction
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict




def insert_users_from_csv():
    file_path = "data/recommend/tn_traveller_master_여행객Master_E.csv"
    # CSV 파일 읽기
    df = pd.read_csv(file_path)
    df = df[['TRAVELER_ID', 'TRAVEL_STATUS_RESIDENCE', 'GENDER', 'AGE_GRP']]
    df.columns = ['username', 'residence_area', 'gender', 'age']  # 컬럼명 매핑

    # Django의 User 모델 가져오기
    User = get_user_model()

    # 각 행의 데이터를 통해 유저 생성
    for _, row in df.iterrows():
        user = User(
            username=row['username'],
            residence_area=row['residence_area'],
            gender=row['gender'],
            age=row['age'],
        )

        # 기본 비밀번호 설정 (랜덤 생성 혹은 고정 값 사용 가능)
        default_password = "password"  # 기본 비밀번호
        user.set_password(default_password)  # 비밀번호 해시 설정

        # 유저 저장
        user.save()

    print("All users inserted successfully")



def insert_visits_from_csv():
    file_path = "data/recommend/tn_visit_area_info_방문지정보_E.csv"
    df = pd.read_csv(file_path)

    # 제외할 방문지 이름 목록
    exclude_names = ['집', '회사', '히사', '사무실']

    # 유효한 시, 군, 구로 끝나는 지역명 목록
    valid_district_endings = ['시', '군', '구']

    # 데이터 삽입
    for index, row in df.iterrows():
        # visit_name 유효성 검사
        visit_name = row['VISIT_AREA_NM'] or ''
        visit_name_clean = visit_name.strip()  # 공백 제거한 방문지 이름

        # 특정 이름이 포함된 경우 제외
        if any(exclude_name in visit_name_clean for exclude_name in exclude_names):
            continue

        # address가 NaN이거나 유효하지 않으면 처리 (비어 있는 경우 제외)
        address = row['ROAD_NM_ADDR']
        if pd.isna(address) or not str(address).strip():  # NaN이거나 비어 있는 주소를 무효로 처리
            continue

        address = str(address).strip()  # 주소를 문자열로 변환하고 공백 제거
        address_parts = address.split(' ')  # 공백으로 분리

        # 주소 요소가 하나인 경우 제외
        if len(address_parts) < 2:
            continue

        # 두 번째 요소가 유효한 시, 군, 구로 끝나는지 확인
        second_element = address_parts[1]  # 두 번째 요소
        if not any(second_element.endswith(valid_suffix) for valid_suffix in valid_district_endings):
            continue

        # 기존에 동일한 visit_name과 address가 존재하는지 확인
        existing_visit = Visit.objects.filter(visit_name=visit_name, address=address).first()
        if existing_visit:
            print(f"Visit already exists: {visit_name}, {address}")
            continue  # 이미 존재하는 경우 건너뜁니다.

        # Visit 객체 생성
        visit = Visit(
            visit_name=visit_name,  # 방문지 이름
            address=address,  # 방문지 주소
            # 사진 필드는 추후에 이미지가 있는 경우에만 추가할 수 있습니다.
            # 예를 들어 row['사진파일경로']가 있다면 아래와 같이 설정 가능
            # photos=row['사진파일경로'] if row['사진파일경로'] else None
        )

        # 데이터베이스에 저장
        visit.save()

    print("All visit data inserted successfully.")


def insert_travels_from_csv():
    rel_cd = {
        "1": '배우자',
        "2": '자녀',
        "3": '부모',
        "4": '조부모',
        "5": '형제 / 자매',
        "6": '친인척',
        "7": '친구',
        "8": '연인',
        "9": '동료',
        "10": "친목 단체/모임(동호회, 종교단체 등)",
        "11": '기타'
    }
    travel_purpose = {
        "1": '쇼핑',
        "2": '테마파크 / 놀이시설 / 동.식물원 방문',
        "3": '역사 유적지 방문',
        "4": '시티투어',
        "5": "야외 스포츠 / 레포츠 활동",
        "6": '지역 문화예술 / 공연 / 전시시설 관람',
        "7": '유흥 / 오락(나이트라이프)',
        "8": '캠핑',
        "9": '지역 축제 / 이벤트 참가',
        "10": '온천 / 스파',
        "11": '교육 / 체험 프로그램 참가',
        "12": '드라마 촬영지 방문',
        "13": '종교 / 성지 순례',
        "21": 'Well-ness 여행',
        "22": 'SNS 인생샷 여행',
        "23": '호캉스 여행',
        "24": '신규 여행지 발굴',
        "25": '반려동물 동반 여행',
        "26": '인플루언서 따라하기 여행',
        "27": '친환경 여행(플로깅 여행)',
        "28": '등반 여행',
    }

    travel_file_path = "data/recommend/tn_travel_여행_E.csv"
    companion_file_path = "data/recommend/tn_companion_info_동반자정보_E.csv"
    visit_file_path = "data/recommend/tn_visit_area_info_방문지정보_E.csv"

    travel_df = pd.read_csv(travel_file_path)
    companion_df = pd.read_csv(companion_file_path)
    visit_df = pd.read_csv(visit_file_path)

    # 필요한 열만 선택
    travel_df = travel_df[
        ['TRAVEL_ID', 'TRAVELER_ID', 'TRAVEL_PURPOSE', 'TRAVEL_START_YMD', 'TRAVEL_END_YMD', 'MVMN_NM']]

    # 동반자 수 계산
    companion_counts = companion_df['TRAVEL_ID'].value_counts()

    # 여행별 방문지 정보를 딕셔너리로 미리 준비
    travel_visits = {}
    for _, row in visit_df.iterrows():
        travel_id = row['TRAVEL_ID']
        if travel_id not in travel_visits:
            travel_visits[travel_id] = []

        # Visit 객체 조회 또는 생성
        visit = Visit.objects.filter(
            visit_name=row['VISIT_AREA_NM'],
            address=row['ROAD_NM_ADDR']
        ).first()

        if visit:
            travel_visits[travel_id].append(visit)

    # 여러 여행 정보를 한 번에 처리하기 위한 리스트
    travel_objects = []

    # 각 여행 정보 삽입
    for _, row in travel_df.iterrows():
        travel_id = row['TRAVEL_ID']
        traveler_id = row['TRAVELER_ID']

        # TRAVEL_PURPOSE 값이 여러 개인 경우 처리
        purposes = row['TRAVEL_PURPOSE'].split(';')  # 세미콜론으로 분리
        travel_names = [travel_purpose.get(purpose.strip(), '기타') for purpose in purposes]  # 각 목적에 대해 이름 조회
        travel_name = ', '.join(travel_names)  # ', '으로 연결

        # 동반자 수 가져오기
        companion_num = companion_counts.get(travel_id, 0)

        # User 모델에서 traveler_id에 해당하는 사용자 가져오기
        try:
            traveler = User.objects.get(pk=traveler_id)
        except User.DoesNotExist:
            print(f"User not found for traveler_id: {traveler_id}")
            continue

        # 동반자 관계 가져오기
        relationships = set(
            rel_cd.get(str(rel)) for rel in companion_df[companion_df['TRAVEL_ID'] == travel_id]['REL_CD'] if
            rel_cd.get(str(rel)) is not None
        )
        relationship = ', '.join(relationships)

        # Travel 객체 생성
        travel = Travel(
            travel_id=travel_id,
            traveler=traveler,
            travel_name=travel_name,
            start_date=row['TRAVEL_START_YMD'],
            end_date=row['TRAVEL_END_YMD'],
            movement_name=row['MVMN_NM'],
            companion_num=companion_num,
            relationship=relationship,
        )
        travel_objects.append(travel)

    # 한 번에 여행 데이터 저장
    Travel.objects.bulk_create(travel_objects)

    # 방문지 정보 설정
    for travel in travel_objects:
        if travel.travel_id in travel_visits:
            # 해당 여행의 방문지들을 설정
            travel.visits.set(travel_visits[travel.travel_id])
        else:
            print(f"No visits found for travel_id: {travel.travel_id}")

    print("All travel data inserted successfully.")

    # 데이터 검증
    print("\nData validation:")
    print(f"Total travels created: {len(travel_objects)}")
    print(f"Travels with visits: {Travel.objects.filter(visits__isnull=False).distinct().count()}")
    # 무작위로 5개 여행을 선택하여 방문지 수 출력
    sample_travels = Travel.objects.order_by('?')[:5]
    print("\nSample travels and their visit counts:")
    for travel in sample_travels:
        visit_count = travel.visits.count()
        print(f"Travel ID: {travel.travel_id}, Visits: {visit_count}")



def insert_transportation_consume_from_csv():
    # CSV 파일 읽기
    file_path = "data/recommend/tn_mvmn_consume_his_이동수단소비내역_E.csv"
    df = pd.read_csv(file_path)

    # 데이터 삽입
    for index, row in df.iterrows():
        travel_id = row['TRAVEL_ID']

        # Travel 모델에서 여행 정보 찾기
        try:
            travel = Travel.objects.get(travel_id=travel_id)
        except Travel.DoesNotExist:
            print(f"여행 ID {travel_id}에 해당하는 여행이 존재하지 않습니다.")
            continue

        # 세부 내용 구성
        details_parts = []
        if pd.notna(row['MVMN_SE_NM']) and row['MVMN_SE_NM'].strip():
            details_parts.append(row['MVMN_SE_NM'])
        if pd.notna(row['STORE_NM']) and row['STORE_NM'].strip():
            details_parts.append(row['STORE_NM'])
        if pd.notna(row['PAYMENT_ETC']) and row['PAYMENT_ETC'].strip():
            details_parts.append(row['PAYMENT_ETC'])

        details = ', '.join(details_parts)  # 세부 내용 연결

        # Consume 객체 생성
        consume = Consume(
            travel=travel,  # 여행과 연결
            category='transportation',  # 이동수단 소비 형태
            consume_name=row['PAYMENT_SE'] or '',  # 소비 항목 이름 (PAYMENT_SE)
            payment_amount=row['PAYMENT_AMT_WON'],  # 결제 금액
            details=details,  # 세부 내용
        )

        # 데이터베이스에 저장
        consume.save()


def insert_lodging_consume_from_csv():
    # CSV 파일 읽기
    file_path = "data/recommend/tn_lodge_consume_his_숙박소비내역_E.csv"
    df = pd.read_csv(file_path)

    # 데이터 삽입
    for index, row in df.iterrows():
        travel_id = row['TRAVEL_ID']

        # Travel 모델에서 여행 정보 찾기
        try:
            travel = Travel.objects.get(travel_id=travel_id)
        except Travel.DoesNotExist:
            print(f"여행 ID {travel_id}에 해당하는 여행이 존재하지 않습니다.")
            continue

        # 세부 내용 구성
        details_parts = []
        if pd.notna(row['LODGING_NM']) and row['LODGING_NM'].strip():
            details_parts.append(row['LODGING_NM'])
        if pd.notna(row['STORE_NM']) and row['STORE_NM'].strip():
            details_parts.append(row['STORE_NM'])
        if pd.notna(row['PAYMENT_ETC']) and row['PAYMENT_ETC'].strip():
            details_parts.append(row['PAYMENT_ETC'])

        details = ', '.join(details_parts)  # 세부 내용 연결

        # Consume 객체 생성
        consume = Consume(
            travel=travel,  # 여행과 연결
            category='lodging',  # 숙박 소비 형태
            consume_name='숙박비',  # 소비 항목 이름 (LODGING_NM)
            payment_amount=row['PAYMENT_AMT_WON'],  # 결제 금액
            details=details,  # 세부 내용
        )

        # 데이터베이스에 저장
        consume.save()


def insert_advance_consume_from_csv():
    file_path = "data/recommend/tn_adv_consume_his_사전소비내역_E.csv"
    df = pd.read_csv(file_path)

    # 데이터 삽입
    for index, row in df.iterrows():
        travel_id = row['TRAVEL_ID']

        # Travel 모델에서 여행 정보 찾기
        try:
            travel = Travel.objects.get(travel_id=travel_id)
        except Travel.DoesNotExist:
            print(f"여행 ID {travel_id}에 해당하는 여행이 존재하지 않습니다.")
            continue

        # 세부 내용 구성
        details_parts = []
        if pd.notna(row['STORE_NM']) and row['STORE_NM'].strip():
            details_parts.append(row['STORE_NM'])
        if pd.notna(row['PAYMENT_ETC']) and row['PAYMENT_ETC'].strip():
            details_parts.append(row['PAYMENT_ETC'])

        details = ', '.join(details_parts)  # 세부 내용 연결

        # Consume 객체 생성
        consume = Consume(
            travel=travel,  # 여행과 연결
            category='advance',  # 사전 소비 형태
            consume_name=row['ADV_NM'] or '',  # 소비 항목 이름 (ADV_NM)
            payment_amount=row['PAYMENT_AMT_WON'],  # 결제 금액
            details=details,  # 세부 내용
        )

        # 데이터베이스에 저장
        consume.save()


def insert_activity_consume_from_csv():
    # ACTIVITY_TYPE_CD와 name을 매핑하는 딕셔너리
    activity_type_mapping = {
        "1": "취식",
        "2": "쇼핑 / 구매",
        "3": "체험 활동 / 입장 및 관람",
        "4": "단순 구경 / 산책 / 걷기",
        "5": "휴식",
        "6": "기타 활동",
        "7": "환승/경유",
        "99": "없음"
    }
    file_path = "data/recommend/tn_activity_consume_his_활동소비내역_E.csv"
    df = pd.read_csv(file_path)

    # 데이터 삽입
    for index, row in df.iterrows():
        travel_id = row['TRAVEL_ID']

        # Travel 모델에서 여행 정보 찾기
        try:
            travel = Travel.objects.get(travel_id=travel_id)
        except Travel.DoesNotExist:
            print(f"여행 ID {travel_id}에 해당하는 여행이 존재하지 않습니다.")
            continue

        # 세부 내용 구성
        details_parts = []
        if pd.notna(row['STORE_NM']) and row['STORE_NM'].strip():
            details_parts.append(row['STORE_NM'])
        if pd.notna(row['PAYMENT_ETC']) and row['PAYMENT_ETC'].strip():
            details_parts.append(row['PAYMENT_ETC'])

        details = ', '.join(details_parts)  # 세부 내용 연결

        # name에 ACTIVITY_TYPE_CD에 따른 값 할당
        activity_type_cd = row['ACTIVITY_TYPE_CD']
        consume_name = activity_type_mapping.get(str(activity_type_cd), "기타 활동")  # 기본값 설정

        # Consume 객체 생성
        consume = Consume(
            travel=travel,  # 여행과 연결
            category='activity',  # 활동 소비 형태
            consume_name=consume_name,  # 소비 항목 이름
            payment_amount=row['PAYMENT_AMT_WON'],  # 결제 금액
            details=details,  # 세부 내용
        )

        # 데이터베이스에 저장
        consume.save()


def insert_consumes_from_csv():
    # 이동수단 소비 내역 삽입
    insert_transportation_consume_from_csv()
    # 숙박 소비 내역 삽입
    insert_lodging_consume_from_csv()
    # 사전 소비 내역 삽입
    insert_advance_consume_from_csv()
    # 활동 소비 내역 삽입
    insert_activity_consume_from_csv()

    print("All consume data inserted successfully.")



def insert_chatbot_touristspot_from_json(file_path, o_tags, a_tags, e_tags):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    tour_info = data['tour_info']
    docu_info = data['docu_info']

    tags = {}  # 태그 정보를 저장할 딕셔너리
    # sentences에서 태그 텍스트를 태그 클래스와 태그 코드에 따라 정리
    for sentence in docu_info.get("sentences", []):
        if not isinstance(sentence, dict):  # sentence가 dict가 아니면 건너뜀
            continue

        annotations = sentence.get("annotations")
        if annotations is None:  # annotations가 None이면 건너뜀
            continue

        for annotation in annotations:
            tag_class = annotation.get("Tagclass")
            tag_code = annotation.get("TagCode")
            tag_text = annotation.get("TagText")

            if tag_class == "O" and tag_code in o_tags:
                tag_name = o_tags[tag_code]
            elif tag_class == "A" and tag_code in a_tags:
                tag_name = a_tags[tag_code]
            elif tag_class == "E" and tag_code in e_tags:
                tag_name = e_tags[tag_code]
            else:
                continue

            # 태그가 이미 존재하면 새로운 텍스트를 추가하고, 없으면 새로 저장
            if tag_name in tags:
                existing_texts = set(tags[tag_name].split(','))  # 중복 방지를 위해 set 사용
                if tag_text not in existing_texts:
                    existing_texts.add(tag_text)
                    tags[tag_name] = ','.join(existing_texts)
            else:
                tags[tag_name] = tag_text

    tourist_spot = TouristSpot(
        touristspot_name=tour_info['Tourist Spot'],
        main_cate=tour_info['Main_cate'],
        second_cate=tour_info['2nd_cate'],
        third_cate=tour_info['3rd_cate'],
        description=docu_info['content'],
        tags=tags,  # tags는 JSONB 형식으로 저장
    )

    tourist_spot.save()
    print(f"{tourist_spot.touristspot_name} data inserted successfully.")


# CSV 파일에서 태그 정보를 읽어오는 함수
def load_tags_by_class(tag_class):
    tags_dict = {}
    filename = f"{tag_class}.csv"  # 예: "A.csv", "O.csv" 등
    file_path = f"data/chatbot/{filename}"
    if os.path.exists(file_path):
        with open(file_path, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            headers = next(reader)  # 첫 번째 줄을 헤더로 읽음
            for row in reader:
                if len(row) == len(headers):  # 데이터의 길이가 헤더와 같을 경우만 처리
                    tag_code = row[1]  # tag_code
                    tag_name = row[0]  # tag_name
                    if tag_code and tag_name:
                        tags_dict[tag_code] = tag_name
    else:
        print(f"Warning: {file_path} not found.")
    return tags_dict


def insert_touristspot_from_json():
    a_tags = load_tags_by_class('A')  # 'A' 클래스의 태그를 로드
    o_tags = load_tags_by_class('O')  # 'O' 클래스의 태그를 로드
    e_tags = load_tags_by_class('E')

    # 디렉터리 경로 설정
    data_path = "data/chatbot/sample_data"

    # 디렉터리 내 모든 파일을 순회
    for file_name in os.listdir(data_path):
        file_path = os.path.join(data_path, file_name)

        # JSON 파일만 처리
        if file_name.endswith(".json"):
            insert_chatbot_touristspot_from_json(file_path, o_tags, a_tags, e_tags)  # save

    for spot in TouristSpot.objects.all():
        spot.save()  # save 메서드가 호출되면서 tags_text 필드가 채워짐

    print("touristspot data inserted successfully.")






# 인기 여행지
def create_popular_tours():
    # 모든 Travel 데이터 가져오기
    travels = Travel.objects.all()

    # 방문지 이름과 주소를 기반으로 방문 횟수 집계
    visit_data = []
    for travel in travels:
        # 각 Travel의 visits 필드에 포함된 Visit 객체들
        for visit in travel.visits.all():
            visit_data.append((visit.visit_name, visit.address))

    # 방문지별 방문 횟수 집계
    visit_counts = Counter(visit_data)

    # 인기 여행지 데이터베이스에 저장
    with transaction.atomic():  # 데이터 무결성을 위해 원자성 보장
        for (visit_name, address), count in visit_counts.items():
            # Visit 객체를 기반으로 PopularTour 생성 또는 업데이트
            visit_instance = Visit.objects.filter(visit_name=visit_name, address=address).first()
            if visit_instance:
                PopularTour.objects.update_or_create(
                    visit=visit_instance,
                    defaults={'visit_count': count}
                )
    print("Popular tours inserted successfully.")





# AI 추천 여행지
def calculate_recommendation_scores():
    # 모든 사용자와 방문지를 가져옵니다
    users = User.objects.all()
    all_visits = list(Visit.objects.all())

    # 각 사용자의 데이터를 저장할 딕셔너리
    user_data = {}
    for user in users:
        # 각 사용자의 여행 정보를 수집
        user_travels = Travel.objects.filter(traveler=user)
        travel_purposes = set()  # 사용자가 참여한 여행 목적들을 저장
        visits = set()  # 사용자가 방문한 장소들을 저장

        # 사용자가 참여한 각 여행에 대해 데이터를 수집
        for travel in user_travels:
            travel_purposes.add(travel.travel_name)  # 여행 목적 추가
            visits.update(travel.visits.all())  # 방문 장소 추가

        # 사용자의 소비 정보를 저장할 딕셔너리
        consume_info = defaultdict(float)
        for consume in Consume.objects.filter(travel__in=user_travels):
            # 소비 카테고리별로 결제 금액을 합산
            consume_info[consume.category] += float(consume.payment_amount)

        # 모든 정보를 user_data 딕셔너리에 저장
        user_data[user] = {
            'purposes': travel_purposes,  # 여행 목적 정보
            'visits': visits,  # 방문 장소 정보
            'consume': consume_info,  # 소비 정보
            'residence_area': user.residence_area,  # 사용자 거주 지역
            'gender': user.gender,  # 사용자 성별
            'age': user.age  # 사용자 나이
        }

    # 각 사용자의 방문 및 소비 데이터를 매트릭스로 변환
    user_visit_matrix = []
    user_consume_matrix = []
    for user in users:
        # 사용자별 방문 벡터 생성 (방문한 곳은 1, 방문하지 않은 곳은 0)
        user_visits = [1 if visit in user_data[user]['visits'] else 0 for visit in all_visits]
        user_visit_matrix.append(user_visits)

        # 사용자별 소비 벡터 생성 (각 소비 카테고리에 대한 금액)
        consume_vector = [user_data[user]['consume'].get(category, 0.0) for category, _ in Consume.TRAVEL_EXPENSE_CATEGORIES]
        user_consume_matrix.append(consume_vector)

    # numpy 배열로 변환하여 유사도 계산에 사용할 수 있도록 함
    user_visit_matrix = np.array(user_visit_matrix)
    user_consume_matrix = np.array(user_consume_matrix)

    # 사용자 간 방문 기록의 코사인 유사도 계산
    visit_similarity = cosine_similarity(user_visit_matrix)
    # 사용자 간 소비 기록의 코사인 유사도 계산
    consume_similarity = cosine_similarity(user_consume_matrix)

    recommendation_objects = []

    # # 하나의 사용자에 대해 테스트 추천 점수를 계산
    # test_user = User.objects.first()
    # for user_index, user in enumerate([test_user]):  # 테스트할 한 명의 유저만 반복문에 포함
    for user_index, user in enumerate(users):
        user_visits = user_data[user]['visits']  # 사용자가 이미 방문한 장소
        user_purposes = user_data[user]['purposes']  # 사용자의 여행 목적들
        user_age = user_data[user]['age']  # 사용자의 나이
        user_residence_area = user_data[user]['residence_area']  # 사용자의 거주 지역
        user_gender = user_data[user]['gender']  # 사용자의 성별

        # 사용자 간 유사도 결합 (방문 유사도와 소비 유사도 가중 평균)
        combined_similarity = 0.6 * visit_similarity[user_index] + 0.3 * consume_similarity[user_index]
        visit_scores = {visit: 0.0 for visit in all_visits}  # 각 방문 장소에 대한 추천 점수를 저장할 딕셔너리

        # 유사한 사용자들의 방문지 정보를 사용해 추천 점수를 계산
        for other_user_index, similarity in enumerate(combined_similarity):
            if user_index != other_user_index and similarity > 0:
                other_user = users[other_user_index]
                other_user_data = user_data[other_user]

                # 사용자와 비교 사용자 간의 추가 정보 기반 유사도 가중치
                additional_weight = 1.0

                # 거주 지역이 같은 경우 추가 가중치
                if user_residence_area and user_residence_area == other_user_data['residence_area']:
                    additional_weight += 0.2  # 거주 지역이 같으면 가중치 증가

                # 성별이 같은 경우 추가 가중치
                if user_gender and user_gender == other_user_data['gender']:
                    additional_weight += 0.1  # 성별이 같으면 가중치 증가

                # 나이 차이가 10세 이하인 경우 추가 가중치
                if user_age and other_user_data['age']:
                    age_difference = abs(user_age - other_user_data['age'])
                    if age_difference <= 10:
                        additional_weight += 0.1  # 나이 차이가 적으면 가중치 증가

                # 유사한 사용자가 방문한 장소들에 대해 점수를 부여
                for visit in other_user_data['visits']:
                    if visit not in user_visits:  # 이미 방문한 장소는 제외
                        # 여행 목적이 유사한 경우 추가 가중치
                        purpose_weight = 1.5 if user_purposes & other_user_data['purposes'] else 1.0
                        # 유사도와 가중치를 반영하여 점수 계산
                        visit_scores[visit] += similarity * purpose_weight * additional_weight

        # # 이미 방문한 장소에 대한 가중치 부여 (추천에서 우선순위가 낮아짐)
        # VISITED_PLACE_WEIGHT = 2.0
        # for visit in user_visits:
        #     visit_scores[visit] *= VISITED_PLACE_WEIGHT

        # 추천 점수를 0~1 사이로 정규화
        max_score = max(visit_scores.values()) if visit_scores else 1
        normalized_scores = {visit: score / max_score for visit, score in visit_scores.items()}

        # 추천 객체 생성 및 저장
        for visit, score in normalized_scores.items():
            recommendation_objects.append(
                Recommendation(
                    user=user,
                    visit=visit,
                    score=score
                )
            )

    # 기존 추천 삭제 후 새로운 추천 목록을 저장
    Recommendation.objects.filter(user__in=users).delete()
    Recommendation.objects.bulk_create(recommendation_objects)

    print("Calculated recommendation scores inserted successfully.")



if __name__ == "__main__":
    # # 유저 정보
    # insert_users_from_csv()

    # # 여행 정보
    # insert_visits_from_csv()
    # insert_travels_from_csv()
    # insert_consumes_from_csv()
    #
    # # chatbot 정보
    # insert_touristspot_from_json()
    #
    #
    # 인기 여행지 정보
    create_popular_tours()


    # 추천 점수
    calculate_recommendation_scores()




    exit()