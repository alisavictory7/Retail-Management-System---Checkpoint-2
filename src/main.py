# src/main.py
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from src.database import get_db, close_db
from src.models import Product, User, Sale, SaleItem, Payment, FailedPaymentLog
from werkzeug.security import generate_password_hash, check_password_hash
import random
from datetime import datetime
from sqlalchemy import not_

app = Flask(__name__, template_folder='../templates')
app.config['SECRET_KEY'] = 'a_very_secret_key'

@app.teardown_appcontext
def teardown_db(exception):
    close_db(exception)

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    products = db.query(Product).all()
    cart = session.get('cart', {'items': [], 'total': 0.0})
    total = sum(float(item['subtotal']) for item in cart.get('items', []))

    recent_sales = db.query(Sale).order_by(Sale.sale_date.desc()).limit(5).all()

    return render_template('index.html', products=products, username=session.get('username'), cart=cart.get('items', []), total=total, recent_sales=recent_sales)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.query(User).filter_by(username=username).first()

        if not user:
            return render_template('login.html', error="Username does not exist.")
        elif not check_password_hash(user.passwordHash, password):
            return render_template('login.html', error="Invalid password. Please try again.")
        else:
            session['user_id'] = user.userID
            session['username'] = user.username
            return redirect(url_for('index'))
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        db = get_db()

        user_exists = db.query(User).filter_by(username=username).first()
        if user_exists:
            return render_template('register.html', error="An account with this username already exists.")

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, passwordHash=hashed_password, email=email)
        db.add(new_user)
        db.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        db = get_db()
        
        product_id_str = request.form.get('product_id')
        quantity_to_add_str = request.form.get('quantity')

        if not product_id_str or not quantity_to_add_str:
            return jsonify({'error': 'Product ID and quantity are required.'}), 400
        
        product_id = int(float(product_id_str))
        quantity_to_add = int(float(quantity_to_add_str))

        product = db.query(Product).filter_by(productID=product_id).first()
        if not product:
            return jsonify({'error': 'Product not found.'}), 404

        cart = session.get('cart', {'items': [], 'total': 0.0})
        item_in_cart = next((item for item in cart['items'] if item['product_id'] == product_id), None)

        current_quantity_in_cart = int(item_in_cart['quantity']) if item_in_cart else 0
        total_quantity_required = current_quantity_in_cart + quantity_to_add

        if product.stock < total_quantity_required:
            error_message = f"Insufficient stock for {product.name}. Only {product.stock} in stock."
            return jsonify({
                'error': error_message,
                'type': 'INSUFFICIENT_STOCK',
                'available_stock': product.stock,
                'product_id': product_id
            }), 400

        if item_in_cart:
            item_in_cart['quantity'] = int(item_in_cart['quantity']) + quantity_to_add
            item_in_cart['subtotal'] = item_in_cart['quantity'] * float(product.price)
        else:
            cart['items'].append({
                'product_id': product.productID,
                'name': product.name,
                'quantity': quantity_to_add,
                'price': float(product.price),
                'subtotal': quantity_to_add * float(product.price)
            })

        cart['total'] = sum(float(item['subtotal']) for item in cart['items'])
        session['cart'] = cart
        session.modified = True

        return jsonify({'success': True, 'cart': cart})
    
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid product ID or quantity format.'}), 400
    except Exception as e:
        print(f"An error occurred in add_to_cart: {e}")
        return jsonify({'error': 'A server error occurred. Please try again later.'}), 500

@app.route('/clear_cart', methods=['POST'])
def clear_cart():
    session['cart'] = {'items': [], 'total': 0.0}
    session.modified = True
    return jsonify({'success': True, 'cart': session['cart']})

@app.route('/purchase', methods=['POST'])
def purchase():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    cart = session.get('cart', {'items': [], 'total': 0.0})
    if not cart['items']:
        return jsonify({'error': 'Your cart is empty.'}), 400
    
    payment_method = request.form.get('payment_method')
    db = get_db()
    
    # More detailed payment simulation
    payment_successful = True
    reason = ""

    if random.random() < 0.3:
        payment_successful = False
        if payment_method == 'Card':
            if random.random() < 0.5:
                reason = "Card Declined by issuer"
            else:
                reason = "Payment processor communication error"
        else:
            reason = "Cash handling error at terminal"

    if not payment_successful:
        log_entry = FailedPaymentLog(
            userID=session['user_id'],
            attempt_date=datetime.utcnow(),
            amount=float(cart['total']),
            payment_method=payment_method,
            reason=reason
        )
        db.add(log_entry)
        db.commit()

        error_message = (
            f"Payment Failure: {reason}. No sale persisted and no stock change. "
            f"Your attempt has been logged with reference ID {log_entry.logID}. Please try another payment method."
        )
        return jsonify({'error': error_message}), 400
    
    try:
        # --- CHANGE HIGHLIGHT: Random concurrency simulation has been removed ---

        # Final stock check before committing the actual user's sale
        for item in cart['items']:
            product = db.query(Product).filter_by(productID=item['product_id']).first()
            if product.stock < int(item['quantity']):
                error_message = (
                    f"Could not complete purchase. Stock for {product.name} changed before checkout. "
                    f"Only {product.stock} left. Please review your cart."
                )
                return jsonify({'error': error_message}), 409

        new_sale = Sale(
            userID=session['user_id'],
            sale_date=datetime.utcnow(),
            totalAmount=float(cart['total'])
        )
        db.add(new_sale)
        db.flush()

        new_payment = Payment(
            saleID=new_sale.saleID,
            payment_date=datetime.utcnow(),
            amount=float(cart['total']),
            payment_method=payment_method,
            status='Completed'
        )
        db.add(new_payment)
        
        for item in cart['items']:
            product = db.query(Product).filter_by(productID=item['product_id']).first()
            product.stock -= int(item['quantity'])
            
            sale_item = SaleItem(
                saleID=new_sale.saleID,
                productID=item['product_id'],
                quantity=int(item['quantity']),
                unit_price=float(item['price']),
                subtotal=float(item['subtotal'])
            )
            db.add(sale_item)
        
        db.commit()

        session['last_sale_id'] = new_sale.saleID
        session['cart'] = {'items': [], 'total': 0.0}
        session.modified = True
        
        return jsonify({
            'message': 'Purchase successful!',
            'receipt_url': url_for('receipt', sale_id=new_sale.saleID)
        })

    except Exception as e:
        db.rollback()
        print(f"An error occurred during purchase: {e}")
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/receipt/<int:sale_id>')
def receipt(sale_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    sale = db.query(Sale).filter_by(saleID=sale_id, userID=session['user_id']).first()
    
    if not sale:
        return "Receipt not found or access denied.", 404
        
    return render_template('receipt.html', sale=sale, username=session['username'])

@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        product_id = int(request.form.get('product_id'))
        cart = session.get('cart', {'items': [], 'total': 0.0})
        cart['items'] = [item for item in cart['items'] if item['product_id'] != product_id]
        cart['total'] = sum(float(item['subtotal']) for item in cart['items'])
        session['cart'] = cart
        session.modified = True
        return jsonify({'success': True, 'cart': cart})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/set_cart_quantity', methods=['POST'])
def set_cart_quantity():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        product_id = int(request.form.get('product_id'))
        quantity = int(request.form.get('quantity'))
        cart = session.get('cart', {'items': [], 'total': 0.0})
        item_in_cart = next((item for item in cart['items'] if item['product_id'] == product_id), None)
        if item_in_cart:
            item_in_cart['quantity'] = quantity
            item_in_cart['subtotal'] = quantity * float(item_in_cart['price'])
        cart['total'] = sum(float(item['subtotal']) for item in cart['items'])
        session['cart'] = cart
        session.modified = True
        return jsonify({'success': True, 'cart': cart})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

