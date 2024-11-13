from django.contrib import admin
from recommend.models import Travel, Consume, Visit



@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ('visit_name', 'address', 'photos')

@admin.register(Travel)
class TravelAdmin(admin.ModelAdmin):
    list_display = ('traveler', 'travel_name', 'start_date', 'end_date', 'movement_name', 'companion_num', 'relationship')
    readonly_fields = ('visits',)


@admin.register(Consume)
class ConsumeAdmin(admin.ModelAdmin):
    list_display = ('category', 'consume_name', 'payment_amount', 'travel', 'details')