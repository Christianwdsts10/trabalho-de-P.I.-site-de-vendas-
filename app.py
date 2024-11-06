from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
from flask_migrate import Migrate
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///store.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['SECRET_KEY'] = 'your_secret_key'  # Chave secreta para sessões
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Modelo de Produto
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(200), nullable=True)

# Modelo de Usuário
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    birthdate = db.Column(db.Date, nullable=False)  # Campo de data de nascimento

# Inicializa o banco de dados
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)

@app.route('/add_product', methods=['POST'])
def add_product():
    name = request.form['name']
    price = request.form['price']

    if 'image' not in request.files:
        return redirect(url_for('index'))

    image_file = request.files['image']
    if image_file.filename == '':
        return redirect(url_for('index'))

    if image_file:
        filename = secure_filename(image_file.filename)
        image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        new_product = Product(name=name, price=float(price), image=filename)
        db.session.add(new_product)
        db.session.commit()

    return redirect(url_for('index'))

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    cart = session.get('cart', {})
    cart[str(product_id)] = cart.get(str(product_id), 0) + \
        1  # Incrementa a quantidade do produto
    session['cart'] = cart
    return redirect(url_for('index'))

@app.route('/cart')
def cart():
    cart = session.get('cart', {})
    cart_items = []
    total_price = 0
    for product_id, quantity in cart.items():
        product = Product.query.get(int(product_id))
        if product:
            cart_items.append({'product': product, 'quantity': quantity})
            total_price += product.price * quantity
    return render_template('cart.html', cart_items=cart_items, total_price=total_price)

@app.route('/remove_from_cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    cart = session.get('cart', {})
    if str(product_id) in cart:
        del cart[str(product_id)]
    session['cart'] = cart
    return redirect(url_for('cart'))

@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        birthdate = request.form.get('birthdate')
        birthdate = datetime.strptime(birthdate, "%Y-%m-%d")

        # Verifica se o email já está em uso
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Este email já está registrado. Tente outro.")
            return redirect(url_for('register'))

        # Calcula a idade
        age = (datetime.now() - birthdate).days // 365
        if age < 16:
            flash("Você precisa ter 16 anos ou mais para se registrar.")
            return redirect(url_for('register'))

        # Criptografa a senha antes de salvar
        hashed_password = generate_password_hash(password)

        # Cria um novo usuário e salva no banco de dados
        new_user = User(username=username, email=email, password=hashed_password, birthdate=birthdate)
        db.session.add(new_user)
        db.session.commit()

        # Marca o usuário como autenticado na sessão
        session['user_authenticated'] = True
        session['user_id'] = new_user.id  # Salva o ID do usuário na sessão

        flash("Cadastro realizado com sucesso!")
        return redirect(url_for('register_success'))

    return render_template('register.html')

# Rota para a página de sucesso de cadastro
@app.route('/register_success')
def register_success():
    return render_template('register_success.html')

# Rota para a página de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_authenticated'] = True
            session['user_id'] = user.id
            flash("Login realizado com sucesso!")
            return redirect(url_for('index'))
        else:
            flash("Email ou senha inválidos. Tente novamente.")
            return redirect(url_for('login'))

    return render_template('login.html')

# Rota para finalizar a compra
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    # Verifica se o usuário está autenticado
    if not session.get('user_authenticated'):
        flash("Por favor, faça o cadastro antes de finalizar a compra.")
        return redirect(url_for('register'))

    # Verifica se o usuário tem 16 anos ou mais
    user = User.query.get(session['user_id'])
    if user:
        age = (datetime.now() - user.birthdate).days // 365
        if age < 16:
            flash("Você precisa ter 16 anos ou mais para realizar compras.")
            return redirect(url_for('index'))

    cart = session.get('cart', {})
    if not cart:
        return redirect(url_for('cart'))

    # Calcular o total do carrinho
    total_price = 0
    for product_id, quantity in cart.items():
        product = Product.query.get(int(product_id))
        if product:
            total_price += product.price * quantity

    if request.method == 'POST':
        payment_method = request.form.get('payment_method')
        installments = request.form.get('installments', 1)

        # Verificar se um método de pagamento foi selecionado
        if not payment_method:
            return redirect(url_for('checkout'))

        return render_template('success.html', total_price=total_price, payment_method=payment_method)

    return render_template('checkout.html', total_price=total_price)

# Rota para Logout
@app.route('/logout')
def logout():
    # Remove os dados de sessão do usuário
    session.pop('user_authenticated', None)
    session.pop('user_id', None)
    flash("Você foi desconectado com sucesso!")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)



