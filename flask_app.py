import mysql.connector
import bcrypt
from flask import Flask, request, render_template, redirect, g, session
from functools import wraps

app = Flask(__name__)
app.secret_key = "clave_secreta_segura"

# ------------------ CONFIGURACIÓN DB ------------------
DB_CONFIG = {
    "host": "michaelmysql.mysql.pythonanywhere-services.com",
    "user": "michaelmysql",
    "password": "Administrador",
    "database": "michaelmysql$default"
}

def get_db():
    if 'db' not in g or not g.db.is_connected():
        g.db = mysql.connector.connect(**DB_CONFIG)
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None and db.is_connected():
        db.close()

# ------------------ DECORADORES ------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "usuario_id" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "usuario_id" not in session or session.get("usuario_rol") != "admin":
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

# ------------------ AUTENTICACIÓN ------------------
@app.route("/")
@login_required
def index():
    return render_template("index.html", usuario=session["usuario_nombre"])

@app.route("/login", methods=["GET", "POST"])
def login():
    db = get_db()
    with db.cursor(dictionary=True) as cursor:
        if request.method == "POST":
            nombre_usuario = request.form.get("nombre_usuario")
            password = request.form.get("password")

            cursor.execute("SELECT * FROM usuarios WHERE nombre_usuario=%s", (nombre_usuario,))
            usuario = cursor.fetchone()

            if usuario and bcrypt.checkpw(password.encode("utf-8"), usuario["password"].encode("utf-8")):
                session["usuario_id"] = usuario["id_usuario"]
                session["usuario_nombre"] = usuario["nombre_usuario"]
                session["usuario_rol"] = usuario["rol"]
                return redirect("/")
            else:
                return render_template("login.html", error="Usuario o contraseña incorrectos")

        return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ------------------ CLIENTES ------------------
@app.route("/clientes", methods=["GET", "POST"])
@login_required
def clientes():
    db = get_db()
    with db.cursor(dictionary=True) as cursor:
        if request.method == "POST":
            nombres = request.form.get("nombres")
            apellidos = request.form.get("apellidos")
            cedula = request.form.get("cedula")
            telefono_fijo = request.form.get("telefono_fijo")
            telefono_celular = request.form.get("telefono_celular")

            cursor.execute("""
                INSERT INTO clientes (nombres, apellidos, cedula, telefono_fijo, telefono_celular)
                VALUES (%s, %s, %s, %s, %s)
            """, (nombres, apellidos, cedula, telefono_fijo, telefono_celular))
            db.commit()
            return redirect("/clientes")

        cursor.execute("SELECT * FROM clientes")
        registros = cursor.fetchall()
        return render_template("clientes.html", registros=registros)

# ------------------ EDITAR CLIENTE ------------------
@app.route("/clientes/editar/<int:id_cliente>", methods=["GET", "POST"])
@login_required
def editar_cliente(id_cliente):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        if request.method == "POST":
            nombres = request.form.get("nombres")
            apellidos = request.form.get("apellidos")
            cedula = request.form.get("cedula")
            telefono_fijo = request.form.get("telefono_fijo")
            telefono_celular = request.form.get("telefono_celular")

            cursor.execute("""
                UPDATE clientes
                SET nombres=%s, apellidos=%s, cedula=%s,
                    telefono_fijo=%s, telefono_celular=%s
                WHERE id_cliente=%s
            """, (nombres, apellidos, cedula, telefono_fijo, telefono_celular, id_cliente))
            db.commit()
            return redirect("/clientes")

        # Obtener datos actuales del cliente
        cursor.execute("SELECT * FROM clientes WHERE id_cliente=%s", (id_cliente,))
        cliente = cursor.fetchone()

        if not cliente:
            return "Error: cliente no encontrado", 404

        return render_template("editar_cliente.html", cliente=cliente)
    finally:
        cursor.close()

#-------------------ELIMINAR CLIENTES-----------------------------
@app.route("/clientes/eliminar/<int:id_cliente>", methods=["POST"])
@login_required
def eliminar_cliente(id_cliente):
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("DELETE FROM equipos WHERE id_cliente=%s", (id_cliente,))
        cursor.execute("DELETE FROM clientes WHERE id_cliente=%s", (id_cliente,))
        db.commit()
    return redirect("/clientes")

# ------------------ EQUIPOS ------------------
@app.route("/equipos", methods=["GET", "POST"])
@login_required
def equipos():
    db = get_db()
    with db.cursor(dictionary=True) as cursor:
        if request.method == "POST":
            id_cliente = request.form.get("id_cliente")
            marca = request.form.get("marca")
            modelo = request.form.get("modelo")
            serie = request.form.get("serie")
            observaciones = request.form.get("observaciones")
            accesorios = request.form.get("accesorios")

            cursor.execute("""
                INSERT INTO equipos (id_cliente, marca, modelo, serie, observaciones, accesorios)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (id_cliente, marca, modelo, serie, observaciones, accesorios))
            db.commit()
            return redirect(f"/ingreso_equipo/{cursor.lastrowid}")

        cursor.execute("""
            SELECT e.id_equipo, e.marca, e.modelo, e.serie,
                   e.observaciones, e.accesorios,
                   c.nombres, c.apellidos, c.id_cliente
            FROM equipos e
            INNER JOIN clientes c ON e.id_cliente = c.id_cliente
        """)
        registros = cursor.fetchall()

        cursor.execute("SELECT * FROM clientes")
        clientes = cursor.fetchall()
        return render_template("equipos.html", registros=registros, clientes=clientes)

# ------------------ INGRESO DE EQUIPO ------------------
@app.route("/ingreso_equipo/<int:id_equipo>")
@login_required
def ingreso_equipo(id_equipo):
    db = get_db()
    with db.cursor(dictionary=True) as cursor:
        cursor.execute("""
            SELECT e.*, c.nombres, c.apellidos
            FROM equipos e
            INNER JOIN clientes c ON e.id_cliente = c.id_cliente
            WHERE e.id_equipo=%s
        """, (id_equipo,))
        equipo = cursor.fetchone()

        if not equipo:
            return "Error: equipo no encontrado", 404

        return render_template("ingreso_equipo.html", equipo=equipo)

# ------------------ EDITAR EQUIPO ------------------
@app.route("/equipos/editar/<int:id_equipo>", methods=["GET", "POST"])
@login_required
def editar_equipo(id_equipo):
    db = get_db()
    with db.cursor(dictionary=True) as cursor:
        if request.method == "POST":
            id_cliente = request.form.get("id_cliente")
            marca = request.form.get("marca")
            modelo = request.form.get("modelo")
            serie = request.form.get("serie")
            observaciones = request.form.get("observaciones")
            accesorios = request.form.get("accesorios")

            cursor.execute("""
                UPDATE equipos
                SET id_cliente=%s, marca=%s, modelo=%s, serie=%s, observaciones=%s, accesorios=%s
                WHERE id_equipo=%s
            """, (id_cliente, marca, modelo, serie, observaciones, accesorios, id_equipo))
            db.commit()
            return redirect("/equipos")

        # Obtener datos actuales del equipo
        cursor.execute("SELECT * FROM equipos WHERE id_equipo=%s", (id_equipo,))
        equipo = cursor.fetchone()

        # Obtener lista de clientes para el menú desplegable
        cursor.execute("SELECT * FROM clientes")
        clientes = cursor.fetchall()

        if not equipo:
            return "Error: equipo no encontrado", 404

        return render_template("editar_equipo.html", equipo=equipo, clientes=clientes)

# ------------------ ELIMINAR EQUIPO ------------------
@app.route("/equipos/eliminar/<int:id_equipo>", methods=["POST"])
@login_required
def eliminar_equipo(id_equipo):
    db = get_db()
    with db.cursor() as cursor:
        # Eliminar el equipo por su ID
        cursor.execute("DELETE FROM equipos WHERE id_equipo=%s", (id_equipo,))
        db.commit()
    return redirect("/equipos")


# ------------------ PRODUCTOS ------------------
@app.route("/productos", methods=["GET", "POST"])
@login_required
def productos():
    db = get_db()
    with db.cursor(dictionary=True) as cursor:
        if request.method == "POST":
            nombre = request.form.get("nombre")
            descripcion = request.form.get("descripcion")
            categoria = request.form.get("categoria")
            precio = request.form.get("precio")
            stock = request.form.get("stock")

            cursor.execute("""
                INSERT INTO productos (nombre, descripcion, categoria, precio, stock)
                VALUES (%s, %s, %s, %s, %s)
            """, (nombre, descripcion, categoria, precio, stock))
            db.commit()
            return redirect("/productos")

        cursor.execute("SELECT * FROM productos")
        registros = cursor.fetchall()
        return render_template("productos.html", registros=registros)

# ------------------ EDITAR PRODUCTO ------------------
@app.route("/productos/editar/<int:id_producto>", methods=["GET", "POST"])
@login_required
def editar_producto(id_producto):
    db = get_db()
    with db.cursor(dictionary=True) as cursor:
        if request.method == "POST":
            nombre = request.form.get("nombre")
            descripcion = request.form.get("descripcion")
            categoria = request.form.get("categoria")
            precio = request.form.get("precio")
            stock = request.form.get("stock")

            cursor.execute("""
                UPDATE productos
                SET nombre=%s, descripcion=%s, categoria=%s, precio=%s, stock=%s
                WHERE id_producto=%s
            """, (nombre, descripcion, categoria, precio, stock, id_producto))
            db.commit()
            return redirect("/productos")

        # Obtener datos actuales del producto para mostrarlos en el formulario
        cursor.execute("SELECT * FROM productos WHERE id_producto=%s", (id_producto,))
        producto = cursor.fetchone()
        return render_template("editar_producto.html", producto=producto)


# ------------------ ELIMINAR PRODUCTO ------------------
@app.route("/productos/eliminar/<int:id_producto>", methods=["POST"])
@login_required
def eliminar_producto(id_producto):
    db = get_db()
    with db.cursor() as cursor:
        # Eliminar el producto por su ID
        # Primero eliminar movimientos asociados al producto
        cursor.execute("DELETE FROM movimientos WHERE id_producto=%s", (id_producto,))
        # Luego eliminar el producto
        cursor.execute("DELETE FROM productos WHERE id_producto=%s", (id_producto,))
        db.commit()
    return redirect("/productos")



# ------------------ MOVIMIENTOS ------------------
@app.route("/movimientos", methods=["GET", "POST"])
@login_required
def movimientos():
    db = get_db()
    with db.cursor(dictionary=True) as cursor:
        if request.method == "POST":
            id_producto = request.form.get("id_producto")
            tipo = request.form.get("tipo")
            cantidad = request.form.get("cantidad")
            observaciones = request.form.get("observaciones")

            cursor.execute("""
                INSERT INTO movimientos (id_producto, tipo, cantidad, observaciones)
                VALUES (%s, %s, %s, %s)
            """, (id_producto, tipo, cantidad, observaciones))
            db.commit()
            return redirect("/movimientos")

        cursor.execute("""
            SELECT m.id_movimiento, p.nombre, m.tipo, m.cantidad, m.fecha, m.observaciones
            FROM movimientos m
            INNER JOIN productos p ON m.id_producto = p.id_producto
            ORDER BY m.fecha DESC
        """)
        registros = cursor.fetchall()

        cursor.execute("SELECT * FROM productos")
        productos = cursor.fetchall()
        return render_template("movimientos.html", registros=registros, productos=productos)

# ------------------ EDITAR MOVIMIENTO ------------------
@app.route("/movimientos/editar/<int:id_movimiento>", methods=["GET", "POST"])
@login_required
def editar_movimiento(id_movimiento):
    db = get_db()
    with db.cursor(dictionary=True) as cursor:
        if request.method == "POST":
            id_producto = request.form.get("id_producto")
            tipo = request.form.get("tipo")
            cantidad = request.form.get("cantidad")
            observaciones = request.form.get("observaciones")

            cursor.execute("""
                UPDATE movimientos
                SET id_producto=%s, tipo=%s, cantidad=%s, observaciones=%s
                WHERE id_movimiento=%s
            """, (id_producto, tipo, cantidad, observaciones, id_movimiento))
            db.commit()
            return redirect("/movimientos")

        # Obtener datos actuales del movimiento
        cursor.execute("SELECT * FROM movimientos WHERE id_movimiento=%s", (id_movimiento,))
        movimiento = cursor.fetchone()

        # Obtener lista de productos para el menú desplegable
        cursor.execute("SELECT * FROM productos")
        productos = cursor.fetchall()

        if not movimiento:
            return "Error: movimiento no encontrado", 404

        return render_template("editar_movimiento.html", movimiento=movimiento, productos=productos)

# ------------------ INFORMES ------------------
@app.route("/informes")
@login_required
def informes():
    db = get_db()
    with db.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT COUNT(*) AS total FROM clientes")
        total_clientes = cursor.fetchone()["total"]

        cursor.execute("""
            SELECT c.id_cliente, c.nombres, c.apellidos, COUNT(e.id_equipo) AS total_equipos
            FROM clientes c
            LEFT JOIN equipos e ON c.id_cliente = e.id_cliente
            GROUP BY c.id_cliente
            ORDER BY total_equipos DESC
            LIMIT 5
        """)
        top_clientes = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) AS total FROM equipos")
        total_equipos = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS total FROM productos")
        total_productos = cursor.fetchone()["total"]

        return render_template(
            "informes.html",
            total_clientes=total_clientes,
            top_clientes=top_clientes,
            total_equipos=total_equipos,
            total_productos=total_productos
        )

# ------------------ USUARIOS ------------------
@app.route("/usuarios", methods=["GET", "POST"])
@admin_required
def usuarios():
    db = get_db()
    with db.cursor(dictionary=True) as cursor:
        if request.method == "POST":
            nombre_usuario = request.form.get("nombre_usuario")
            password = request.form.get("password")
            rol = request.form.get("rol")

            # Encriptar la contraseña
            hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

            cursor.execute("""
                INSERT INTO usuarios (nombre_usuario, password, rol)
                VALUES (%s, %s, %s)
            """, (nombre_usuario, hashed, rol))
            db.commit()
            return redirect("/usuarios")

        cursor.execute("SELECT id_usuario, nombre_usuario, rol FROM usuarios")
        registros = cursor.fetchall()
        return render_template("usuarios.html", registros=registros)


@app.route("/usuarios/editar/<int:id_usuario>", methods=["GET", "POST"])
@admin_required
def editar_usuario(id_usuario):
    db = get_db()
    with db.cursor(dictionary=True) as cursor:
        if request.method == "POST":
            nombre_usuario = request.form.get("nombre_usuario")
            rol = request.form.get("rol")
            password = request.form.get("password")

            if password and password.strip():
                hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                cursor.execute("""
                    UPDATE usuarios
                    SET nombre_usuario=%s, rol=%s, password=%s
                    WHERE id_usuario=%s
                """, (nombre_usuario, rol, hashed, id_usuario))
            else:
                cursor.execute("""
                    UPDATE usuarios
                    SET nombre_usuario=%s, rol=%s
                    WHERE id_usuario=%s
                """, (nombre_usuario, rol, id_usuario))

            db.commit()
            return redirect("/usuarios")

        cursor.execute("SELECT id_usuario, nombre_usuario, rol FROM usuarios WHERE id_usuario=%s", (id_usuario,))
        usuario = cursor.fetchone()
        return render_template("editar_usuario.html", usuario=usuario)


@app.route("/usuarios/eliminar/<int:id_usuario>", methods=["POST"])
@admin_required
def eliminar_usuario(id_usuario):
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("DELETE FROM usuarios WHERE id_usuario=%s", (id_usuario,))
        db.commit()
    return redirect("/usuarios")



