from django import forms
from recommend.models import Travel, TRAVEL_PURPOSE_CHOICES


class TravelForm(forms.ModelForm):
    class Meta:
        model = Travel
        fields = ['travel_name', 'start_date', 'end_date', 'movement_name', 'companion_num', 'relationship']

    # 선택할 수 있는 여행 목적 필드 추가
    travel_name = forms.MultipleChoiceField(
        choices=TRAVEL_PURPOSE_CHOICES,
        widget=forms.CheckboxSelectMultiple,  # 체크박스를 사용하여 여러 개 선택
    )

    # 날짜 필드 수정
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),  # 날짜 형식 입력을 위해 date 타입 사용
        required=True,
    )

    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),  # 날짜 형식 입력을 위해 date 타입 사용
        required=True,
    )

    # start_date와 end_date 비교하여 검증 추가
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date:
            if end_date < start_date:
                self.add_error('end_date', 'End date must be after the start date.')

        return cleaned_data

    def clean_travel_name(self):
        travel_names = self.cleaned_data.get('travel_name')
        return ', '.join(travel_names)  # 선택된 여행 목적을 ', '로 연결