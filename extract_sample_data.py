import os
import shutil
import random

def sample_random_json_files(root_dir, sample_dir, sample_interval=1000):
    # sample_data 폴더 생성
    os.makedirs(sample_dir, exist_ok=True)

    json_files = []
    # 모든 하위 폴더에서 JSON 파일 수집
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.json'):
                json_files.append(os.path.join(root, file))

    # 1000개씩 그룹으로 나누고 각 그룹에서 랜덤으로 하나 선택
    for i in range(0, len(json_files), sample_interval):
        # 현재 그룹의 파일 목록
        group_files = json_files[i:i + sample_interval]
        if group_files:
            # 그룹에서 랜덤으로 하나 선택
            selected_file = random.choice(group_files)
            try:
                # 파일 이름 추출
                file_name = os.path.basename(selected_file)
                # sample_data 폴더로 파일 복사
                shutil.copy(selected_file, os.path.join(sample_dir, file_name))
            except Exception as e:
                print(f"Error copying {selected_file}: {e}")

    print(f"각 1000개 그룹에서 랜덤으로 선택한 파일을 {sample_dir} 폴더에 저장했습니다.")




if __name__ == "__main__":
    root_directory = 'data/chatbot/labeling_data'  # 원본 JSON 파일들이 들어있는 최상위 폴더 경로
    sample_directory = 'data/chatbot/sample_data'  # 샘플링된 JSON 파일들을 저장할 폴더
    sample_random_json_files(root_directory, sample_directory)
