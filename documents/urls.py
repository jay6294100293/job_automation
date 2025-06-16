# documents/urls.py
from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [

    path('generate/<int:application_id>/', views.GenerateDocumentsView.as_view(), name='generate'),
    path('download/<int:application_id>/', views.DownloadDocumentsView.as_view(), name='download'),
    path('download-all/<int:search_id>/', views.DownloadAllDocumentsView.as_view(), name='download_all'),
    path('preview/<int:application_id>/<str:doc_type>/', views.PreviewDocumentView.as_view(), name='preview'),
    # # Document management
    # path('preview/<int:application_id>/', views.DocumentPreviewView.as_view(), name='preview'),
    # path('download/<int:application_id>/', views.DocumentDownloadView.as_view(), name='download'),
    # path('download/<int:application_id>/<str:doc_type>/', views.SingleDocumentDownloadView.as_view(),
    #      name='download_single'),
    #
    # # Document generation
    # path('generate/<int:application_id>/', views.GenerateDocumentsView.as_view(), name='generate'),
    # path('regenerate/<int:application_id>/', views.RegenerateDocumentsView.as_view(), name='regenerate'),
    #
    # # Document status
    # path('status/<int:application_id>/', views.DocumentStatusView.as_view(), name='status'),
]