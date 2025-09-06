EcoFinds - Sustainable Second-Hand Marketplace
EcoFinds is a full-stack web application designed as a vibrant and trusted platform that revolutionizes the way people buy and sell pre-owned goods. The project aims to foster a culture of sustainability by extending the lifecycle of products, reducing waste, and providing an accessible and convenient alternative to purchasing new items.

This application was developed to fulfill the problem statement for the Odoo x NMIT Hackathon '25, focusing on core user authentication and product listing functionalities.

Key Features
The application implements all the core features outlined in the project wireframes:

Dual User Roles: Supports both regular users (buyers/sellers) and a separate Inventory Manager with distinct dashboards and permissions.

User Authentication: Secure user registration and login system for both roles.

Product Listing Feed: A main shop page where users can browse all available second-hand items.

Search and Filter: Users can search for products by keywords in the title and filter listings by category.

Product Detail Pages: Each product has a dedicated page showing its title, description, price, category, and an image placeholder.

User-Managed Listings (CRUD): Logged-in users can create, view, edit, and delete their own product listings from a dedicated "My Listings" page.

Shopping Cart: A functional shopping cart where users can add items before purchasing.

Purchase History: A page for users to view a list of products they have purchased in the past.

User Dashboard: A profile page where users can view and update their personal information.

Inventory Management System: A complete, original dashboard for an Inventory Manager to handle stock, forecast demand, and manage products centrally.

Technology Stack
Backend: Python with Flask Framework

Database: MySQL

Frontend: HTML, CSS, JavaScript

Getting Started
Follow these instructions to get a copy of the project up and running on your local machine for development and testing purposes.

Prerequisites
Python 3.x

Git

MySQL Server

Installation
Clone the repository

Open your terminal and clone the GitHub repository to your local machine:

git clone [https://github.com/Niranjan5168/EcoFinds---Sustainable-Second-Hand-Marketplace.git](https://github.com/Niranjan5168/EcoFinds---Sustainable-Second-Hand-Marketplace.git)
cd EcoFinds---Sustainable-Second-Hand-Marketplace

Create a virtual environment

It's a best practice to create a virtual environment for your Python projects.

# For macOS/Linux
python3 -m venv venv
source venv/bin/activate

# For Windows
python -m venv venv
.\venv\Scripts\activate

Install dependencies

Create a file named requirements.txt in the project's root directory and add the following lines:

Flask
mysql-connector-python
requests
statsmodels
pandas
numpy
joblib
scikit-learn

Now, install these dependencies using pip:

pip install -r requirements.txt

Set up the MySQL Database

Log in to your MySQL client from the terminal:

mysql -u root -p

Create the database and tables by running the following SQL script.

CREATE DATABASE IF NOT EXISTS dbms;
USE dbms;

CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone_number VARCHAR(20) UNIQUE,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    seller_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    market_price DECIMAL(10, 2) NOT NULL,
    image_url VARCHAR(255) DEFAULT 'placeholder.jpg',
    is_sold BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (seller_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE cart (
    cart_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT DEFAULT 1,
    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
);

CREATE TABLE orders (
    order_no INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    order_quantity INT NOT NULL,
    order_status VARCHAR(50) DEFAULT 'completed',
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE order_items (
    item_id INT AUTO_INCREMENT PRIMARY KEY,
    o_no INT NOT NULL,
    pid INT NOT NULL,
    product_name VARCHAR(255),
    quantity INT NOT NULL,
    sale_price DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (o_no) REFERENCES orders(order_no) ON DELETE CASCADE
);

Configure the Application

Open the app.py file and ensure the db_config dictionary matches your MySQL username and password.

Run the Flask Application

python3 app.py

The application will be running at http://127.0.0.1:5000.

How to Use
You can use the sample data to test the application's features.

Regular User Login (Seller/Buyer):

User ID: 2

Password: charliepass

This user can browse the shop, buy items, and manage their own listings on the "My Listings" page.