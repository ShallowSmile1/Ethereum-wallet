from django.urls import path

from .views import home_page, signup_page, transaction_page, send_token_page, log_out

urlpatterns = [
    path('', home_page, name='Home'),
    path('transactions/', transaction_page, name='Transactions'), 
    path('transactions/new/', send_token_page, name='New_token'),
    path('signup/', signup_page, name='Signup'),
    path('signout/', log_out, name='Logout')
]
