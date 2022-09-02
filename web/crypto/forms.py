from django import forms


class TokenForm(forms.Form):
    address = forms.CharField()
    value = forms.IntegerField()

class UserForm(forms.Form):
    phone = forms.CharField(max_length=18)
    password = forms.CharField(max_length=20)