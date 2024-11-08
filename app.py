from flask import Flask, render_template, redirect, url_for, request, session, flash  
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
from flask_migrate import Migrate
from flask import Flask, render_template, request, redirect, url_for, session, jsonify

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
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1  # Incrementa a quantidade do produto
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

        # Verifica se todos os campos foram preenchidos
        if not username or not email or not password:
            flash("Por favor, preencha todos os campos.")
            return render_template('register.html')

        # Verifica se o email já está em uso
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Este email já está registrado. Você já tem uma conta. Por favor, faça o login.")
            return redirect(url_for('login'))  # Redireciona para a página de login

        # Criptografa a senha antes de salvar
        hashed_password = generate_password_hash(password)

        # Cria um novo usuário e salva no banco de dados
        try:
            new_user = User(username=username, email=email, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()

            # Marca o usuário como autenticado na sessão
            session['user_authenticated'] = True
            session['user_id'] = new_user.id  # Salva o ID do usuário na sessão

            flash("Cadastro realizado com sucesso!")
            return redirect(url_for('register_success'))
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao cadastrar: {str(e)}")
            return render_template('register.html')

    return render_template('register.html')

# Rota para a página de sucesso de cadastro
@app.route('/register_success')
def register_success():
    return render_template('register_success.html')

# Rota para a página de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_or_email = request.form.get('username_or_email')
        password = request.form.get('password')

        # Tentar encontrar o usuário pelo nome de usuário ou e-mail
        user = User.query.filter((User.username == username_or_email) | (User.email == username_or_email)).first()
        
        # Verificar se o usuário existe e se a senha está correta
        if user and check_password_hash(user.password, password):
            session['user_authenticated'] = True
            session['user_id'] = user.id
            flash("Login realizado com sucesso!")
            return redirect(url_for('welcome'))  # Redireciona para a página de boas-vindas
        else:
            flash("Email, nome de usuário ou senha inválidos. Tente novamente.")
            return redirect(url_for('login'))

    return render_template('login.html')

# Rota de boas-vindas
@app.route('/welcome')
def welcome():
    user_id = session.get('user_id')
    
    # Verifica se o usuário está autenticado
    if not user_id:
        flash("Você precisa estar logado para acessar esta página.")
        return redirect(url_for('login'))
    
    user = User.query.get(user_id)
    return render_template('welcome.html', username=user.username)  # Passa o nome do usuário para o template

# Rota para finalizar a compra
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if not session.get('user_authenticated'):
        flash("Por favor, faça o cadastro antes de finalizar a compra.")
        return redirect(url_for('register'))

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

        if not payment_method:
            return redirect(url_for('checkout'))

        # Salvar informações da compra na sessão
        session['total_price'] = total_price
        session['payment_method'] = payment_method

        if payment_method == 'boleto':
            flash("Pagamento via boleto selecionado.")
        elif payment_method == 'card':
            flash(f"Pagamento com cartão de crédito em {installments}x.")
        elif payment_method == 'pix':
            flash("Pagamento via Pix selecionado.")

        return redirect(url_for('success'))  # Redireciona para a página de sucesso

    return render_template('checkout.html', total_price=total_price)

@app.route('/limpar_carrinho', methods=['POST'])
def limpar_carrinho():
    session.pop('cart', None)  # Limpa o carrinho da sessão
    return jsonify({'success': True})  # Retorna um JSON de sucesso

# Rota para a página de sucesso da compra
@app.route('/success')
def success():
    # Limpa o carrinho após o sucesso da compra
    session.pop('cart', None)  # Limpa o carrinho da sessão
    return render_template('success.html', 
                           total_price=session.get('total_price'), 
                           payment_method=session.get('payment_method'))

# Rota para Logout
@app.route('/logout')
def logout():
    session.pop('user_authenticated', None)
    session.pop('user_id', None)
    flash("Você foi desconectado com sucesso!")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)













