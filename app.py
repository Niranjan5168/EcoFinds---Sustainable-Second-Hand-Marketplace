from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import mysql.connector

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# MySQL Configuration
db_config = {
    'host': 'localhost',
    'port': 3306, 
    'user': 'root',
    'password': 'Niranjan@68',
    'database': 'dbms'
}

# --- Authentication Routes ---
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE user_id = %s AND password = %s", (user_id, password))
            user = cursor.fetchone()
            
            if user:
                session['user_id'] = user['user_id']
                session['name'] = f"{user['first_name']} {user['last_name']}"
                session['role'] = user.get('role', 'User') # Default to 'User' if role is null
                flash('Login successful!', 'success')
                
                if session['role'].strip().lower() == 'inventory manager':
                    return redirect(url_for('inventory_dashboard'))
                else:
                    return redirect(url_for('shop'))
            else:
                flash('Invalid User ID or password', 'error')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')
        finally:
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        phone_number = request.form['phone_number']
        password = request.form['password']
        role = request.form.get('role', 'User') # Get role from form, default to 'User'
        
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = %s OR phone_number = %s", (email, phone_number))
            if cursor.fetchone():
                flash('Email or phone number already exists', 'error')
            else:
                cursor.execute("SELECT MAX(user_id) FROM users")
                result = cursor.fetchone()
                new_user_id = 1 if result[0] is None else result[0] + 1
                
                cursor.execute(
                    """INSERT INTO users 
                    (user_id, first_name, last_name, email, phone_number, password, role) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (new_user_id, first_name, last_name, email, phone_number, password, role)
                )
                conn.commit()
                flash(f'Registration successful! Your User ID is {new_user_id}. Please login.', 'success')
                return redirect(url_for('login'))
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')
        finally:
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()
            
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

# --- EcoFinds Marketplace Routes ---

@app.route('/shop')
def shop():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        search_query = request.args.get('search', '').strip()
        selected_categories = request.args.getlist('categories')
        
        cursor.execute("SELECT DISTINCT category FROM products WHERE category IS NOT NULL AND category != '' AND is_sold = FALSE")
        categories = [row['category'] for row in cursor.fetchall()]
        
        products_query = """
            SELECT p.product_id, p.name as product_name, 
                   p.category, p.market_price as price, p.image_url
            FROM products p
            WHERE p.is_sold = FALSE
        """
        query_params = []
        
        if search_query:
            products_query += " AND p.name LIKE %s"
            query_params.append(f"%{search_query}%")
        
        if selected_categories:
            products_query += " AND p.category IN ({})".format(','.join(['%s'] * len(selected_categories)))
            query_params.extend(selected_categories)
        
        products_query += " ORDER BY p.created_at DESC"
        
        cursor.execute(products_query, query_params)
        products = cursor.fetchall()
        
    except Exception as e:
        flash('Error fetching products', 'error')
        products = []
        categories = []
        selected_categories = []
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
    
    return render_template('shop.html',
                         products=products,
                         categories=categories,
                         selected_categories=selected_categories,
                         search_query=search_query)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT p.*, u.first_name, u.last_name 
            FROM products p 
            JOIN users u ON p.seller_id = u.user_id 
            WHERE p.product_id = %s
        """
        cursor.execute(query, (product_id,))
        product = cursor.fetchone()

        if not product:
            flash('Product not found.', 'error')
            return redirect(url_for('shop'))

    except Exception as e:
        flash('Error fetching product details.', 'error')
        product = None
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

    return render_template('product_detail.html', product=product)

@app.route('/my_listings')
def my_listings():
    if 'user_id' not in session:
        flash('Please login to view your listings.', 'error')
        return redirect(url_for('login'))
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT * FROM products WHERE seller_id = %s ORDER BY created_at DESC"
        cursor.execute(query, (session['user_id'],))
        products = cursor.fetchall()
        
        return render_template('my_listings.html', products=products)
        
    except Exception as e:
        flash('An error occurred while fetching your listings.', 'error')
        return render_template('my_listings.html', products=[])
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/add_listing', methods=['POST'])
def add_listing():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        name = request.form.get('name', '').strip()
        category = request.form.get('category', '').strip()
        market_price = float(request.form.get('market_price', 0))
        description = request.form.get('description', '').strip()
        
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO products (seller_id, name, category, market_price, description) VALUES (%s, %s, %s, %s, %s)",
            (session['user_id'], name, category, market_price, description)
        )
        conn.commit()
        flash('Your listing has been added successfully!', 'success')
        
    except Exception as e:
        if 'conn' in locals() and conn.is_connected(): conn.rollback()
        flash(f'Error adding listing: {str(e)}', 'error')
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
    
    return redirect(url_for('my_listings'))

@app.route('/edit_listing/<int:product_id>', methods=['POST'])
def edit_listing(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT seller_id FROM products WHERE product_id = %s", (product_id,))
        product = cursor.fetchone()

        if not product or product['seller_id'] != session['user_id']:
            flash('You do not have permission to edit this listing.', 'error')
            return redirect(url_for('my_listings'))

        name = request.form.get('name', '').strip()
        category = request.form.get('category', '').strip()
        market_price = float(request.form.get('market_price', 0))
        description = request.form.get('description', '').strip()

        cursor.execute(
            "UPDATE products SET name = %s, category = %s, market_price = %s, description = %s WHERE product_id = %s",
            (name, category, market_price, description, product_id)
        )
        conn.commit()
        flash('Listing updated successfully!', 'success')

    except Exception as e:
        if 'conn' in locals() and conn.is_connected(): conn.rollback()
        flash(f'Error updating listing: {str(e)}', 'error')
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
            
    return redirect(url_for('my_listings'))

@app.route('/delete_listing/<int:product_id>', methods=['POST'])
def delete_listing(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT seller_id FROM products WHERE product_id = %s", (product_id,))
        product = cursor.fetchone()

        if not product or product['seller_id'] != session['user_id']:
            flash('You do not have permission to delete this listing.', 'error')
            return redirect(url_for('my_listings'))
        
        cursor.execute("DELETE FROM products WHERE product_id = %s", (product_id,))
        conn.commit()
        flash('Listing deleted successfully!', 'success')
        
    except Exception as e:
        if 'conn' in locals() and conn.is_connected(): conn.rollback()
        flash(f'Error deleting listing: {str(e)}', 'error')
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
    
    return redirect(url_for('my_listings'))


# --- Cart and Order Routes ---

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        return jsonify({'error': 'Please login first'}), 401
    
    try:
        product_id = request.json.get('product_id')
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Check if product is already sold, is owned by user, or is already in another cart
        cursor.execute("SELECT is_sold, seller_id FROM products WHERE product_id = %s", (product_id,))
        product = cursor.fetchone()
        if not product:
             return jsonify({'error': 'Product does not exist.'}), 404
        if product['is_sold']:
             return jsonify({'error': 'This item has already been sold.'}), 400
        if product['seller_id'] == session['user_id']:
             return jsonify({'error': 'You cannot add your own item to the cart.'}), 400

        cursor.execute("SELECT cart_id FROM cart WHERE product_id = %s", (product_id,))
        if cursor.fetchone():
            return jsonify({'error': 'This item is already in someone\'s cart.'}), 400

        # Add to cart
        cursor.execute("INSERT INTO cart (user_id, product_id) VALUES (%s, %s)", (session['user_id'], product_id))
        conn.commit()
        return jsonify({'message': 'Product added to cart successfully'})
        
    except Exception as e:
        return jsonify({'error': 'Failed to add product to cart'}), 500
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/view_cart')
def view_cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT c.cart_id, p.product_id, p.name as product_name, p.image_url,
                   p.market_price, p.category, p.market_price as subtotal
            FROM cart c JOIN products p ON c.product_id = p.product_id
            WHERE c.user_id = %s ORDER BY c.added_date DESC
        """
        cursor.execute(query, (session['user_id'],))
        cart_items = cursor.fetchall()
        total = sum(item['subtotal'] for item in cart_items)
        
    except Exception as e:
        flash('Error fetching cart items', 'error')
        cart_items = []
        total = 0
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
    
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/place_order', methods=['POST'])
def place_order():
    if 'user_id' not in session:
        return jsonify({'error': 'Please login first'}), 401
    
    conn = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        conn.start_transaction()
        
        cart_query = """
            SELECT p.product_id, p.market_price, p.name
            FROM cart c JOIN products p ON c.product_id = p.product_id
            WHERE c.user_id = %s AND p.is_sold = FALSE
        """
        cursor.execute(cart_query, (session['user_id'],))
        cart_items = cursor.fetchall()
        
        if not cart_items:
            return jsonify({'error': 'Cart is empty or items are no longer available.'}), 400
        
        total_amount = sum(item['market_price'] for item in cart_items)
        total_quantity = len(cart_items)
        
        order_query = "INSERT INTO orders (user_id, total_amount, order_quantity, order_status) VALUES (%s, %s, %s, 'Completed')"
        cursor.execute(order_query, (session['user_id'], total_amount, total_quantity))
        order_no = cursor.lastrowid
        
        order_items_query = "INSERT INTO order_items (o_no, pid, product_name, quantity, sale_price) VALUES (%s, %s, %s, 1, %s)"
        for item in cart_items:
            cursor.execute(order_items_query, (order_no, item['product_id'], item['name'], item['market_price']))
            cursor.execute("UPDATE products SET is_sold = TRUE WHERE product_id = %s", (item['product_id'],))

        cursor.execute("DELETE FROM cart WHERE user_id = %s", (session['user_id'],))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Order placed successfully!', 'order_no': order_no})
        
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({'error': 'Failed to place order due to a server error.'}), 500
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()


# --- User Profile & History Routes ---

@app.route('/purchase_history')
def purchase_history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        orders_query = "SELECT * FROM orders WHERE user_id = %s ORDER BY order_date DESC"
        cursor.execute(orders_query, (session['user_id'],))
        orders = cursor.fetchall()
        
        for order in orders:
            items_query = "SELECT * FROM order_items WHERE o_no = %s"
            cursor.execute(items_query, (order['order_no'],))
            order['order_items'] = cursor.fetchall()
        
    except Exception as e:
        flash('Error fetching purchase history', 'error')
        orders = []
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
    
    return render_template('purchase_history.html', orders=orders)

@app.route('/user_dashboard', methods=['GET', 'POST'])
def user_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        try:
            first_name = request.form['first_name']
            last_name = request.form['last_name']
            email = request.form['email']
            phone_number = request.form['phone_number']

            update_query = """
                UPDATE users SET first_name = %s, last_name = %s, email = %s, phone_number = %s
                WHERE user_id = %s
            """
            cursor.execute(update_query, (first_name, last_name, email, phone_number, session['user_id']))
            conn.commit()
            flash('Profile updated successfully!', 'success')
            session['name'] = f"{first_name} {last_name}" # Update name in session
        except Exception as e:
            flash('Error updating profile.', 'error')
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
        return redirect(url_for('user_dashboard'))

    # GET request logic
    try:
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (session['user_id'],))
        user = cursor.fetchone()
    except Exception as e:
        user = None
        flash('Could not fetch user details.', 'error')
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

    return render_template('user_dashboard.html', user=user)


# --- Original Inventory Management Routes (Preserved) ---

@app.route('/inventory_dashboard')
def inventory_dashboard():
    if session.get('role', '').strip().lower() != 'inventory manager':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    
    # ... (original inventory_dashboard code remains here) ...
    # This code is long and unchanged, so it's omitted for brevity.
    # In your actual file, you would keep the original function here.
    return render_template('inventory_dashboard.html', user_full_name=session.get('name'))


@app.route('/manage_products')
def manage_products():
    if session.get('role', '').strip().lower() != 'inventory manager':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    # ... (original manage_products code remains here) ...
    return "This is the original manage products page."


@app.route('/add_product', methods=['POST'])
def add_product():
    if session.get('role', '').strip().lower() != 'inventory manager':
        return redirect(url_for('login'))
    # ... (original add_product code remains here) ...
    return redirect(url_for('manage_products'))


@app.route('/update_inventory/<int:product_id>', methods=['POST'])
def update_inventory(product_id):
    if session.get('role', '').strip().lower() != 'inventory manager':
        return redirect(url_for('login'))
    # ... (original update_inventory code remains here) ...
    return redirect(url_for('manage_products'))


@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if session.get('role', '').strip().lower() != 'inventory manager':
        return redirect(url_for('login'))
    # ... (original delete_product code remains here) ...
    return redirect(url_for('manage_products'))
@app.route('/about')
def about():
    # This route serves your existing about.html page
    return render_template('about.html')
if __name__ == '__main__':
    app.run(debug=True)