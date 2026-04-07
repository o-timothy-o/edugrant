from django.urls import path

from . import views

app_name = "programs"

urlpatterns = [
    path('my-applications/', views.my_applications_view, name='my_applications'),
    path('list/', views.program_list_applicant_view, name='program_list_applicant'),
    path('apply/spark/', views.spark_application_view, name='spark_application'),
    path('apply/spark/step2/<int:application_id>/', views.spark_application_step2_view, name='spark_application_step2'),
    path('apply/sinag/', views.sinag_application_view, name='sinag_application'),
    path('apply/sinag/step2/<int:application_id>/', views.sinag_application_step2_view, name='sinag_application_step2'),
    path('apply/<int:program_id>/', views.generic_application_step1_view, name='generic_application_step1'),
    path('apply/<int:program_id>/step2/<int:application_id>/', views.generic_application_step2_view, name='generic_application_step2'),
    path('application/<int:application_id>/', views.application_detail_view, name='application_detail'),
    path('application/<int:application_id>/review/', views.application_review_view, name='application_review'),
]
