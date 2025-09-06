from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import mysql.connector
from flask_bcrypt import Bcrypt
import re
import dns.resolver

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
bcrypt = Bcrypt(app)

# MySQL Configuration
db_config = {
    'host': 'localhost',
    'port': 3306, 
    'user': 'root',
    'password': 'Niranjan@68',
    'database': 'dbms'
}

@app.context_processor
def inject_cart_count():
    cart_count = 0
    if 'user_id' in session:
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM cart WHERE user_id = %s", (session['user_id'],))
            result = cursor.fetchone()
            if result:
                cart_count = result[0]
        except Exception as e:
            print(f"Error fetching cart count: {e}")
        finally:
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()
    return dict(cart_count=cart_count)

# --- Routes ---

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/shop')
def shop():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get all parameters from URL
    category = request.args.get('category')
    search_query = request.args.get('search')
    sort_by = request.args.get('sort_by', 'newest')
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')
    group_by = request.args.get('group_by')

    products = None
    categories = None
    grouped_products = None
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        # --- Build Dynamic Query ---
        base_query = "SELECT * FROM products WHERE is_sold = FALSE"
        params = []
        
        # Filter conditions
        if search_query:
            base_query += " AND name LIKE %s"
            params.append(f"%{search_query}%")
        if category:
            base_query += " AND category = %s"
            params.append(category)
        if min_price:
            base_query += " AND market_price >= %s"
            params.append(float(min_price))
        if max_price:
            base_query += " AND market_price <= %s"
            params.append(float(max_price))

        # Sorting options
        sort_options = {
            'newest': 'ORDER BY created_at DESC',
            'price_asc': 'ORDER BY market_price ASC',
            'price_desc': 'ORDER BY market_price DESC'
        }
        order_clause = sort_options.get(sort_by, 'ORDER BY created_at DESC')
        
        # Only run product query if there are filters or a category is selected
        if search_query or category or min_price or max_price:
            query = f"{base_query} {order_clause}"
            cursor.execute(query, tuple(params))
            products = cursor.fetchall()

            # Handle Group By option
            if group_by == 'category' and products:
                grouped_products = {}
                for product in products:
                    cat = product.get('category', 'Uncategorized')
                    if cat not in grouped_products:
                        grouped_products[cat] = []
                    grouped_products[cat].append(product)
        else:
            # Default view: Fetch all unique categories
            query = "SELECT category, COUNT(*) as product_count FROM products WHERE is_sold = FALSE AND category IS NOT NULL AND category != '' GROUP BY category ORDER BY category"
            cursor.execute(query)
            categories = cursor.fetchall()
        
        # Add first_image to products if they exist
        if products is not None:
             for product in products:
                if product.get('image_url'):
                    product['first_image'] = product['image_url'].split(',')[0].strip()
                else:
                    product['first_image'] = 'placeholder.jpg'

        return render_template(
            'shop.html', 
            products=products, 
            categories=categories, 
            category_name=category, 
            search_query=search_query, 
            current_sort=sort_by,
            min_price=min_price,
            max_price=max_price,
            group_by=group_by,
            grouped_products=grouped_products
        )

    except Exception as e:
        flash(f'Error loading shop page: {e}', 'error')
        return render_template('shop.html', categories=[], products=None)
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

# (The rest of your app.py file remains the same...)




# --- Helper Function for Email Validation ---
def is_email_valid(email):
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return False
    try:
        domain = email.split('@')[1]
        records = dns.resolver.resolve(domain, 'MX')
        return len(records) > 0
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.Timeout):
        return False


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            
            if user and bcrypt.check_password_hash(user['password'], password):
                session['user_id'] = user['user_id']
                session['name'] = user['first_name']
                session['role'] = user.get('role', 'User')
                flash('Login successful!', 'success')
                
                if session['role'].strip().lower() == 'inventory manager':
                    return redirect(url_for('inventory_dashboard'))
                else:
                    return redirect(url_for('shop'))
            else:
                flash('Invalid email or password. Please try again.', 'error')
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
        display_name = request.form['display_name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if not is_email_valid(email):
            flash('Please enter a valid and deliverable email address.', 'error')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Passwords do not match. Please try again.', 'error')
            return redirect(url_for('register'))

        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                flash('An account with this email already exists.', 'error')
            else:
                hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
                cursor.execute("SELECT MAX(user_id) FROM users")
                result = cursor.fetchone()
                new_user_id = 1 if result[0] is None else result[0] + 1
                
                cursor.execute(
                    """INSERT INTO users 
                    (user_id, first_name, last_name, email, password, role) 
                    VALUES (%s, %s, %s, %s, %s, %s)""",
                    (new_user_id, display_name, '', email, hashed_password, 'User')
                )
                conn.commit()
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('login'))
        except Exception as e:
            flash(f'An error occurred during registration: {str(e)}', 'error')
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

# --- You can copy the other routes from the previous response here ---
# --- (product_detail, my_listings, add_listing, cart, orders, etc.) ---
@app.route('/product/<int:product_id>')
def product_detail(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT p.*, u.first_name FROM products p JOIN users u ON p.seller_id = u.user_id WHERE p.product_id = %s"
        cursor.execute(query, (product_id,))
        product = cursor.fetchone()

        if not product:
            flash('Product not found.', 'error')
            return redirect(url_for('shop'))

        if product.get('image_url'):
            product['image_list'] = [img.strip() for img in product['image_url'].split(',')]
        else:
            product['image_list'] = ['placeholder.jpg']

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
        return redirect(url_for('login'))
    
    search_query = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'newest')

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        base_query = "SELECT * FROM products WHERE seller_id = %s"
        params = [session['user_id']]

        if search_query:
            base_query += " AND name LIKE %s"
            params.append(f"%{search_query}%")
        
        sort_options = {
            'newest': 'ORDER BY created_at DESC',
            'price_asc': 'ORDER BY market_price ASC',
            'price_desc': 'ORDER BY market_price DESC'
        }
        order_clause = sort_options.get(sort_by, 'ORDER BY created_at DESC')
        
        query = f"{base_query} {order_clause}"
        cursor.execute(query, tuple(params))
        products = cursor.fetchall()

        for product in products:
            if product.get('image_url'):
                product['first_image'] = product['image_url'].split(',')[0].strip()
            else:
                product['first_image'] = 'placeholder.jpg'

        return render_template(
            'my_listings.html', 
            products=products, 
            search_query=search_query, 
            current_sort=sort_by
        )
        
    except Exception as e:
        flash(f'An error occurred: {e}', 'error')
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
        # Fetch all new fields from the form
        name = request.form.get('name')
        category = request.form.get('category')
        description = request.form.get('description')
        market_price = request.form.get('market_price')
        condition = request.form.get('condition')
        brand = request.form.get('brand')
        model = request.form.get('model')
        year = request.form.get('year_of_manufacture')
        color = request.form.get('color')
        packaging = 'has_original_packaging' in request.form
        manual = 'has_manual' in request.form
        image_urls = request.form.get('image_urls')
        
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        sql = """
            INSERT INTO products (
                seller_id, name, category, description, market_price, `condition`, 
                brand, model, year_of_manufacture, color, has_original_packaging, 
                has_manual, image_url
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            session['user_id'], name, category, description, market_price, condition,
            brand, model, year if year else None, color, 
            packaging, manual, image_urls
        )
        cursor.execute(sql, values)
        conn.commit()
        flash('Your listing has been added!', 'success')
        
    except Exception as e:
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
        # Fetch all fields from the edit form
        name = request.form.get('name')
        category = request.form.get('category')
        description = request.form.get('description')
        market_price = request.form.get('market_price')
        condition = request.form.get('condition')
        brand = request.form.get('brand')
        model = request.form.get('model')
        year = request.form.get('year_of_manufacture')
        color = request.form.get('color')
        packaging = 'has_original_packaging' in request.form
        manual = 'has_manual' in request.form
        image_urls = request.form.get('image_urls')

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Security Check: Make sure the user owns this product
        cursor.execute("SELECT seller_id FROM products WHERE product_id = %s", (product_id,))
        product_owner = cursor.fetchone()
        if not product_owner or product_owner[0] != session['user_id']:
            flash('You do not have permission to edit this listing.', 'error')
            return redirect(url_for('my_listings'))

        sql = """
            UPDATE products SET
                name = %s, category = %s, description = %s, market_price = %s, 
                `condition` = %s, brand = %s, model = %s, year_of_manufacture = %s, 
                color = %s, has_original_packaging = %s, has_manual = %s, image_url = %s
            WHERE product_id = %s
        """
        values = (
            name, category, description, market_price, condition, brand, model,
            year if year else None, color, packaging, manual, image_urls, product_id
        )
        cursor.execute(sql, values)
        conn.commit()
        flash('Listing updated successfully!', 'success')

    except Exception as e:
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

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        return jsonify({'error': 'Please login first'}), 401
    
    try:
        product_id = request.json.get('product_id')
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

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

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/purchase_history')
def purchase_history():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    search_query = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'newest')

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        # Base query to get all items the user has purchased
        base_query = """
            SELECT oi.product_name, oi.sale_price, p.category, o.order_date, u_seller.first_name as seller_name
            FROM order_items oi
            JOIN orders o ON oi.o_no = o.order_no
            JOIN products p ON oi.pid = p.product_id
            JOIN users u_seller ON p.seller_id = u_seller.user_id
            WHERE o.user_id = %s
        """
        params = [session['user_id']]

        if search_query:
            base_query += " AND oi.product_name LIKE %s"
            params.append(f"%{search_query}%")

        sort_options = {
            'newest': 'ORDER BY o.order_date DESC',
            'oldest': 'ORDER BY o.order_date ASC',
            'price_desc': 'ORDER BY oi.sale_price DESC',
            'price_asc': 'ORDER BY oi.sale_price ASC'
        }
        order_clause = sort_options.get(sort_by, 'ORDER BY o.order_date DESC')
        
        final_query = f"{base_query} {order_clause}"
        
        cursor.execute(final_query, tuple(params))
        purchased_items = cursor.fetchall()
        
    except Exception as e:
        flash(f'Error fetching purchase history: {e}', 'error')
        purchased_items = []
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
    
    return render_template(
        'purchase_history.html', 
        purchased_items=purchased_items,
        search_query=search_query,
        current_sort=sort_by
    )
@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    if 'user_id' not in session:
        return jsonify({'error': 'Please login first'}), 401
    
    try:
        cart_id = request.json.get('cart_id')
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # Security check: Ensure the item belongs to the current user before deleting
        cursor.execute(
            "DELETE FROM cart WHERE cart_id = %s AND user_id = %s", 
            (cart_id, session['user_id'])
        )
        
        # Check if a row was actually deleted
        if cursor.rowcount > 0:
            conn.commit()
            return jsonify({'success': True, 'message': 'Item removed successfully'})
        else:
            return jsonify({'error': 'Item not found or you do not have permission to remove it'}), 404

    except Exception as e:
        return jsonify({'error': f'An error occurred: {e}'}), 500
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
            
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
            session['name'] = f"{first_name} {last_name}"
        except Exception as e:
            flash('Error updating profile.', 'error')
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
        return redirect(url_for('user_dashboard'))

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
    return render_template('inventory_dashboard.html', user_full_name=session.get('name'))

@app.route('/manage_products')
def manage_products():
    if session.get('role', '').strip().lower() != 'inventory manager':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    return "This is the original manage products page."

@app.route('/add_product', methods=['POST'])
def add_product():
    if session.get('role', '').strip().lower() != 'inventory manager':
        return redirect(url_for('login'))
    return redirect(url_for('manage_products'))

@app.route('/update_inventory/<int:product_id>', methods=['POST'])
def update_inventory(product_id):
    if session.get('role', '').strip().lower() != 'inventory manager':
        return redirect(url_for('login'))
    return redirect(url_for('manage_products'))

@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if session.get('role', '').strip().lower() != 'inventory manager':
        return redirect(url_for('login'))
    return redirect(url_for('manage_products'))

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    app.run(debug=True)

