# documents/urls.py
from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [

    path('generate/<int:application_id>/', views.GenerateDocumentsView.as_view(), name='generate'),
    path('download/<int:application_id>/', views.DownloadDocumentsView.as_view(), name='download'),
    path('download-all/<int:search_id>/', views.DownloadAllDocumentsView.as_view(), name='download_all'),
    path('preview/<int:application_id>/<str:doc_type>/', views.PreviewDocumentView.as_view(), name='preview'),

]