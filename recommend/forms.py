from django import forms
from recommend.models import Travel, TRAVEL_PURPOSE_CHOICES


class TravelForm(forms.ModelForm):
    class Meta:
        model = Travel
        fields = ['traveler', 'travel_name', 'start_date', 'end_date', 'movement_name', 'companion_num', 'relationship']

    # 선택할 수 있는 여행 목적 필드 추가
    travel_name = forms.MultipleChoiceField(
        choices=TRAVEL_PURPOSE_CHOICES,
        widget=forms.CheckboxSelectMultiple,  # 체크박스를 사용하여 여러 개 선택
    )

    def clean_travel_name(self):
        travel_names = self.cleaned_data.get('travel_name')
        return ', '.join(travel_names)  # 선택된 여행 목적을 ', '로 연결
