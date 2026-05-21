from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
import hashlib
import json
import os
from functools import wraps
import csv
from io import StringIO

app = Flask(__name__)
app.config['SECRET_KEY'] = 'kasirku-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kasirku.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)
db = SQLAlchemy(app)

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE MODELS
# ─────────────────────────────────────────────────────────────────────────────

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user')

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    harga = db.Column(db.Integer, nullable=False)
    stok = db.Column(db.Integer, default=0)
    barcode = db.Column(db.String(100), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tanggal = db.Column(db.String(10), nullable=False)
    jam = db.Column(db.String(8), nullable=False)
    produk = db.Column(db.String(100), nullable=False)
    harga = db.Column(db.Integer, nullable=False)
    metode = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), default='Terbeli')
    sisa_stok = db.Column(db.Integer)
    info = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ─────────────────────────────────────────────────────────────────────────────
# AUTHENTICATION
# ─────────────────────────────────────────────────────────────────────────────

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        user = User.query.get(session['user_id'])
        if not user or user.role != 'admin':
            return jsonify({'error': 'Forbidden'}), 403
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    user = User.query.filter_by(username=username).first()
    if not user or user.password != hash_password(password):
        return jsonify({'error': 'Username atau Password salah'}), 401
    
    session['user_id'] = user.id
    session['username'] = user.username
    session['role'] = user.role
    
    return jsonify({
        'success': True,
        'username': user.username,
        'role': user.role
    })

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/auth/check', methods=['GET'])
def check_auth():
    if 'user_id' in session:
        return jsonify({
            'authenticated': True,
            'username': session.get('username'),
            'role': session.get('role')
        })
    return jsonify({'authenticated': False})

# ─────────────────────────────────────────────────────────────────────────────
# PRODUCTS API
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/products', methods=['GET'])
@login_required
def get_products():
    products = Product.query.all()
    return jsonify([{
        'id': p.id,
        'nama': p.nama,
        'harga': p.harga,
        'stok': p.stok,
        'barcode': p.barcode or ''
    } for p in products])

@app.route('/api/products', methods=['POST'])
@login_required
def create_product():
    data = request.json
    
    if not data.get('nama') or not data.get('harga'):
        return jsonify({'error': 'Data tidak lengkap'}), 400
    
    product = Product(
        nama=data['nama'],
        harga=int(data['harga']),
        stok=int(data.get('stok', 0)),
        barcode=data.get('barcode', '').strip() or None
    )
    
    try:
        db.session.add(product)
        db.session.commit()
        return jsonify({
            'id': product.id,
            'nama': product.nama,
            'harga': product.harga,
            'stok': product.stok,
            'barcode': product.barcode or ''
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/api/products/<int:product_id>', methods=['PUT'])
@login_required
def update_product(product_id):
    product = Product.query.get_or_404(product_id)
    data = request.json
    
    product.nama = data.get('nama', product.nama)
    product.harga = int(data.get('harga', product.harga))
    product.stok = int(data.get('stok', product.stok))
    if data.get('barcode'):
        product.barcode = data['barcode'].strip() or None
    
    try:
        db.session.commit()
        return jsonify({
            'id': product.id,
            'nama': product.nama,
            'harga': product.harga,
            'stok': product.stok,
            'barcode': product.barcode or ''
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/products/barcode/<barcode>', methods=['GET'])
@login_required
def get_product_by_barcode(barcode):
    product = Product.query.filter_by(barcode=barcode).first()
    if not product:
        return jsonify({'error': 'Produk tidak ditemukan'}), 404
    return jsonify({
        'id': product.id,
        'nama': product.nama,
        'harga': product.harga,
        'stok': product.stok,
        'barcode': product.barcode
    })

# ─────────────────────────────────────────────────────────────────────────────
# TRANSACTIONS API
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/transactions', methods=['POST'])
@login_required
def create_transaction():
    data = request.json
    items = data.get('items', [])
    metode = data.get('metode', 'Cash')
    
    now = datetime.now()
    tanggal = now.strftime("%Y-%m-%d")
    jam = now.strftime("%H:%M:%S")
    
    transactions = []
    
    for item in items:
        product = Product.query.get(item['id'])
        if not product or product.stok < item['quantity']:
            db.session.rollback()
            return jsonify({'error': f'Stok {product.nama} tidak cukup'}), 400
        
        product.stok -= item['quantity']
        
        txn = Transaction(
            tanggal=tanggal,
            jam=jam,
            produk=product.nama,
            harga=item['harga'],
            metode=metode,
            sisa_stok=product.stok,
            info=data.get('info', '')
        )
        
        db.session.add(txn)
        transactions.append(txn)
    
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'tanggal': tanggal,
            'jam': jam,
            'count': len(transactions)
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/api/transactions', methods=['GET'])
@login_required
def get_transactions():
    filter_type = request.args.get('filter', 'semua')
    today = date.today()
    
    if filter_type == 'hari':
        str_today = today.strftime("%Y-%m-%d")
        transactions = Transaction.query.filter_by(tanggal=str_today).all()
    elif filter_type == 'minggu':
        monday = today - timedelta(days=today.weekday())
        str_mon = monday.strftime("%Y-%m-%d")
        transactions = Transaction.query.filter(Transaction.tanggal >= str_mon).all()
    elif filter_type == 'bulan':
        str_bulan = today.strftime("%Y-%m")
        transactions = Transaction.query.filter(Transaction.tanggal.startswith(str_bulan)).all()
    else:
        transactions = Transaction.query.all()
    
    return jsonify([{
        'id': t.id,
        'tanggal': t.tanggal,
        'jam': t.jam,
        'produk': t.produk,
        'harga': t.harga,
        'metode': t.metode,
        'status': t.status,
        'sisa_stok': t.sisa_stok,
        'info': t.info
    } for t in transactions])

@app.route('/api/transactions/reset', methods=['DELETE'])
@admin_required
def reset_transactions():
    Transaction.query.delete()
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/transactions/stats', methods=['GET'])
@login_required
def get_stats():
    today = date.today()
    
    all_txns = Transaction.query.all()
    hari_txns = Transaction.query.filter_by(tanggal=today.strftime("%Y-%m-%d")).all()
    
    monday = today - timedelta(days=today.weekday())
    minggu_txns = Transaction.query.filter(Transaction.tanggal >= monday.strftime("%Y-%m-%d")).all()
    
    str_bulan = today.strftime("%Y-%m")
    bulan_txns = Transaction.query.filter(Transaction.tanggal.startswith(str_bulan)).all()
    
    cash_txns = Transaction.query.filter(Transaction.metode.ilike('%cash%')).all()
    qris_txns = Transaction.query.filter(Transaction.metode.ilike('%qris%')).all()
    lain_txns = Transaction.query.filter(
        ~Transaction.metode.ilike('%cash%'),
        ~Transaction.metode.ilike('%qris%')
    ).all()
    
    def total(txns):
        return sum(t.harga for t in txns)
    
    return jsonify({
        'grand_total': total(all_txns),
        'grand_count': len(all_txns),
        'hari_total': total(hari_txns),
        'hari_count': len(hari_txns),
        'minggu_total': total(minggu_txns),
        'minggu_count': len(minggu_txns),
        'bulan_total': total(bulan_txns),
        'bulan_count': len(bulan_txns),
        'cash_total': total(cash_txns),
        'qris_total': total(qris_txns),
        'lain_total': total(lain_txns)
    })

# ─────────────────────────────────────────────────────────────────────────────
# ACCOUNT MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/account/change-password', methods=['POST'])
@login_required
def change_password():
    data = request.json
    user = User.query.get(session['user_id'])
    
    if user.password != hash_password(data.get('old_password', '')):
        return jsonify({'error': 'Password lama salah'}), 400
    
    if len(data.get('new_password', '')) < 6:
        return jsonify({'error': 'Password minimal 6 karakter'}), 400
    
    if data.get('new_password') != data.get('confirm_password'):
        return jsonify({'error': 'Konfirmasi password tidak cocok'}), 400
    
    user.password = hash_password(data['new_password'])
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Password berhasil diubah'})

@app.route('/api/admin/change-user-password', methods=['POST'])
@admin_required
def admin_change_password():
    data = request.json
    user = User.query.filter_by(username=data.get('username')).first()
    
    if not user:
        return jsonify({'error': 'User tidak ditemukan'}), 404
    
    user.password = hash_password(data.get('new_password'))
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Password user berhasil diubah'})

# ─────────────────────────────────────────────────────────────────────────────
# IMPORT/EXPORT
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/products/import-csv', methods=['POST'])
@admin_required
def import_csv():
    if 'file' not in request.files:
        return jsonify({'error': 'File tidak ditemukan'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'File tidak dipilih'}), 400
    
    try:
        stream = StringIO(file.stream.read().decode("utf-8"))
        reader = csv.reader(stream)
        next(reader, None)  # Skip header
        
        count = 0
        for row in reader:
            if len(row) >= 4:
                product = Product(
                    nama=row[2],
                    harga=int(float(row[3])),
                    stok=int(row[4]) if len(row) > 4 else 0,
                    barcode=row[5].strip() if len(row) > 5 else None
                )
                db.session.add(product)
                count += 1
        
        db.session.commit()
        return jsonify({'success': True, 'imported': count})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# ─────────────────────────────────────────────────────────────────────────────
# INIT DB
# ─────────────────────────────────────────────────────────────────────────────

def init_db():
    with app.app_context():
        db.create_all()
        
        # Create default accounts if not exist
        if User.query.filter_by(username='admin').first() is None:
            admin = User(
                username='admin',
                password=hash_password('admin123'),
                role='admin'
            )
            db.session.add(admin)
        
        if User.query.filter_by(username='kasir').first() is None:
            kasir = User(
                username='kasir',
                password=hash_password('kasir123'),
                role='user'
            )
            db.session.add(kasir)
        
        db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
