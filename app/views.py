from flask import render_template, flash, redirect, session, url_for, request, g
from flask_login import login_user, logout_user, current_user, login_required
from app import app, db, lm
from forms import LoginForm, EditForm, PostForm, SearchForm
from models import User, Post
from emails import follower_notification
from flask_bcrypt import generate_password_hash, check_password_hash
from datetime import datetime
from config import POSTS_PER_PAGE, MAX_SEARCH_RESULTS

@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@app.route('/index/<int:page>', methods=['GET', 'POST'])
@login_required
def index(page=1):
	form = PostForm()
	if form.validate_on_submit():
		post = Post(body=form.post.data, timestamp=datetime.utcnow(), author=g.user)
		db.session.add(post)
		db.session.commit()
		flash('Your post is now live!')
		return redirect(url_for('index'))
	posts = g.user.followed_posts().paginate(page, POSTS_PER_PAGE, False)
	return render_template('index.html',
						   title='Home',
						   form=form,
						   posts=posts)

@app.route('/register', methods=['GET', 'POST'])
def register():
	if g.user is not None and g.user.is_authenticated:
		return redirect(url_for('index'))
	error = None
	if request.method == 'POST':
		if not request.form['username']:
			error = 'You have to enter a username'
		elif not request.form['email'] or \
				'@' not in request.form['email']:
			error = 'You have to enter a valid email address'
		elif not request.form['password']:
			error = 'You have to enter a password'
		elif request.form['password'] != request.form['password2']:
			error = 'The two passwords do not match'
		elif User.query.filter_by(username = request.form['username']).first() is not None:
			error = 'The username is already taken'
		else:
			user = User(request.form['username'], request.form['email'],
							generate_password_hash(request.form['password']))
			db.session.add(user)
			db.session.commit()
			flash('You were successfully registered and can login now')
			return redirect(url_for('login'))
	return render_template('register.html', error=error)


@app.route('/login', methods=['GET', 'POST'])
def login():
	#if g.user is not None and g.user.is_authenticated:
		#return redirect(url_for('index'))
	error = None
	form = LoginForm()	
	if form.validate_on_submit():
		user = User.query.filter_by(username=form.username.data).first()
		if user is None:
			error = 'user does not exist' 
		elif not check_password_hash(user.pwhash, form.password.data):
			error = 'Password is false, please try again'			
		else:
			login_user(user)
			flash('Logged in successfully')
			return redirect(url_for('index'))	
		
	return render_template('login.html', title='Sign In', form=form,
							error=error)

@lm.user_loader
def load_user(id):
	return User.query.get(int(id))

@app.before_request
def before_request():
	g.user = current_user
	if g.user.is_authenticated:
		g.user.last_seen = datetime.utcnow()
		db.session.add(g.user)
		db.session.commit()
		g.search_form = SearchForm()


@app.route('/logout')
def logout():
	logout_user()
	return redirect(url_for('index'))

@app.route('/user/<username>')
@app.route('/user/<username>/<int:page>')
@login_required
def user(username, page=1):
	user = User.query.filter_by(username=username).first()
	if user is None:
		flash('User %s not found.' % username)
		return redirect(url_for('index'))
	posts = user.posts.paginate(page, POSTS_PER_PAGE, False)
	return render_template('user.html',
						   user=user,
						   posts=posts)

@app.route('/edit', methods=['GET', 'POST'])
@login_required
def edit():
	form = EditForm(g.user.username)
	if form.validate_on_submit():
		g.user.username = form.username.data
		g.user.about_me = form.about_me.data
		db.session.add(g.user)
		db.session.commit()
		flash('Your changes have been saved.')
		return redirect(url_for('edit'))
	else:
		form.username.data = g.user.username
		form.about_me.data = g.user.about_me
	return render_template('edit.html', form=form)

@app.route('/search', methods=['POST'])
@login_required
def search():
	if not g.search_form.validate_on_submit():
		return redirect(url_for('index'))
	return redirect(url_for('search_results', query=g.search_form.search.data))

@app.route('/search_results/<query>')
@login_required
def search_results(query):
	results = Post.query.whoosh_search(query, MAX_SEARCH_RESULTS).all()
	return render_template('search_results.html',
						   query=query,
						   results=results)

@app.route('/follow/<username>')
@login_required
def follow(username):
	user = User.query.filter_by(username=username).first()
	if user is None:
		flash('User %s not found.' % username)
		return redirect(url_for('index'))
	if user == g.user:
		flash('You can\'t follow yourself!')
		return redirect(url_for('user', username=username))
	u = g.user.follow(user)
	if u is None:
		flash('Cannot follow ' + username + '.')
		return redirect(url_for('user', username=username))
	db.session.add(u)
	db.session.commit()
	flash('You are now following ' + username + '!')
	follower_notification(user, g.user)
	return redirect(url_for('user', username=username))

@app.route('/unfollow/<username>')
@login_required
def unfollow(username):
	user = User.query.filter_by(username=username).first()
	if user is None:
		flash('User %s not found.' % username)
		return redirect(url_for('index'))
	if user == g.user:
		flash('You can\'t unfollow yourself!')
		return redirect(url_for('user', username=username))
	u = g.user.unfollow(user)
	if u is None:
		flash('Cannot unfollow ' + username + '.')
		return redirect(url_for('user', username=username))
	db.session.add(u)
	db.session.commit()
	flash('You have stopped following ' + username + '.')
	return redirect(url_for('user', username=username))

@app.errorhandler(404)
def not_found_error(error):
	return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
	db.session.rollback()
	return render_template('500.html'), 500