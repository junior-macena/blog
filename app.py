from flask import Flask, render_template, redirect, url_for, request, flash
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, current_user, logout_user, login_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.exc import IntegrityError
from sqlalchemy import desc
from werkzeug.utils import secure_filename
import os

# Inicializa a aplicação Flask e o banco de dados
app = Flask("hello")
db_url = os.environ.get("DATABASE_URL") or "sqlite:///app.db"
app.config["SQLALCHEMY_DATABASE_URI"] = db_url.replace("postgres", "postgresql")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "pudim"

db = SQLAlchemy(app)
login = LoginManager(app)

# Define o modelo Post
class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(70), nullable=False)
    body = db.Column(db.String(500))
    image = db.Column(db.String(200))
    created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

# Define o modelo User com gerenciamento de senhas
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(20), nullable=False, unique=True, index=True) 
    email = db.Column(db.String(64), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    posts = db.relationship('Post', backref='author')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Carrega o usuário para a sessão atual
@login.user_loader
def load_user(id):
    return User.query.get(int(id))

# Rota da página inicial para exibir todos os posts
@app.route("/")
def index():
    posts = Post.query.order_by(desc(Post.created)).all()  # Obtém os posts em ordem decrescente de criação
    return render_template("index.html", posts=posts)

# Rota de registro para novos usuários
@app.route('/register', methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == "POST":
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Verifica se as senhas coincidem
        if password != confirm_password:
            flash("As senhas não coincidem!")
            return redirect(url_for('register'))

        try:
            new_user = User(username=username, email=email, is_admin=False) 
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Usuário ou E-mail já existe!")
        else:
            return redirect(url_for('login'))
    return render_template('register.html')

# Rota de login para usuários existentes
@app.route('/login', methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash("Usuário ou Senha incorretos!")
            return redirect(url_for('login'))
        login_user(user)
        return redirect(url_for('index'))
    return render_template("login.html")

# Rota de logout para usuários
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

# Rota para criar novos posts
@app.route('/create', methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        title = request.form['title']
        body = request.form['body']
        image = request.files.get('image')

        image_filename = None
        if image:
            image_filename = secure_filename(image.filename)
            image.save(os.path.join('static/images', image_filename))  # Salva a imagem no diretório

        try:
            post = Post(title=title, body=body, image=image_filename, author=current_user) 
            db.session.add(post)
            db.session.commit()
            return redirect(url_for('index'))
        except IntegrityError:
            flash("Erro ao criar Postagem, tente novamente mais tarde")
    return render_template('create.html')

# Rota para editar posts existentes
@app.route('/edit/<int:post_id>', methods=["GET", "POST"])
@login_required
def edit(post_id):
    post = Post.query.get_or_404(post_id)
    
    if post.author != current_user and not current_user.is_admin:
        flash("Você não tem permissão para editar esta postagem.")
        return redirect(url_for('index'))
    
    if request.method == "POST":
        post.title = request.form['title']
        post.body = request.form['body']
        image = request.files.get('image')

        if image:
            image_filename = secure_filename(image.filename)
            image.save(os.path.join('static/images', image_filename)) 
            post.image = image_filename  

        db.session.commit()
        return redirect(url_for('index'))

    return render_template('edit.html', post=post)

# Rota para excluir posts
@app.route('/delete/<int:post_id>', methods=["POST"])
@login_required
def delete(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author == current_user or current_user.is_admin:
        db.session.delete(post)
        db.session.commit()
        flash("Postagem excluída com sucesso.")
    else:
        flash("Você não tem permissão para excluir esta postagem.")
    return redirect(url_for('index'))

# Inicializa o banco de dados e cria um usuário admin se necessário
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        # Verifica se o usuário admin já existe
        admin_user = User.query.filter_by(username='junior').first()
        if admin_user is None:
            admin_user = User(username='junior', email='junior@gmail.com', is_admin=True) 
            admin_user.set_password('123')  
            db.session.add(admin_user)
            db.session.commit() 

    app.run(debug=True)
