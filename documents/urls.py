# documents/urls.py
from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [

    path('generate/<int:application_id>/', views.GenerateDocumentsView.as_view(), name='generate'),
    path('download/<int:application_id>/', views.DownloadDocumentsView.as_view(), name='download'),
    path('download-all/<int:search_id>/', views.DownloadAllDocumentsView.as_view(), name='download_all'),
    path('preview/<int:application_id>/<str:doc_type>/', views.PreviewDocumentView.as_view(), name='preview'),
    # Additional required URLs
    path('single/<int:document_id>/', views.DownloadSingleDocumentView.as_view(), name='download_single'),
    path('regenerate/<int:application_id>/<str:doc_type>/', views.RegenerateDocumentView.as_view(), name='regenerate'),
    path('bulk-action/', views.BulkDocumentActionView.as_view(), name='bulk_action'),
    path('status/<int:application_id>/', views.DocumentStatusView.as_view(), name='status'),
    path('application-docs/<int:application_id>/', views.ApplicationDocumentsView.as_view(),
         name='application_documents'),

    # Download options
    path('download-options/', views.DownloadOptionsView.as_view(), name='download_options'),
]

