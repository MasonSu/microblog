from flask_wtf import Form
from wtforms import StringField, BooleanField, TextAreaField
from wtforms.validators import InputRequired, DataRequired, Length
from app.models import User

class RegisterForm(Form):
	username = StringField('username', validators=[InputRequired()])
	email = StringField('email', validators=[InputRequired()])
	password = StringField('password', validators=[InputRequired()])
	password2 = StringField('password2', validators=[InputRequired()])

class LoginForm(Form):
	username = StringField('username', validators=[InputRequired()])
	password = StringField('password', validators=[InputRequired()])
	
	#remember_me = BooleanField('remember_me', default=False)

class EditForm(Form):
	username = StringField('username', validators=[InputRequired()])
	about_me = TextAreaField('about_me', validators=[Length(min=0, max=140)])

	def __init__(self, original_username, *args, **kwargs):
		Form.__init__(self, *args, **kwargs)
		self.original_username = original_username

	def validate(self):
		if not Form.validate(self):
			return False
		if self.username.data == self.original_username:
			return True
		user = User.query.filter_by(username=self.username.data).first()
		if user != None:
			self.username.errors.append('This username is already in use. Please choose another one.')
			return False
		return True

class PostForm(Form):
	post = StringField('post', validators=[InputRequired()])

class SearchForm(Form):
	search = StringField('search', validators=[InputRequired()])