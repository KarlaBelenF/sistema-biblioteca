CREATE DATABASE BIBLIOTECA;
USE BIBLIOTECA;

-- CREACION DE TABLAS

CREATE TABLE UBICACION(
	id int primary key auto_increment,
    estante int not null, 
    fila int not null, 
    UNIQUE(estante,fila)
);
CREATE TABLE LIBRO(
	id int primary key auto_increment, 
    codigo varchar(80) unique not null, 
    titulo varchar(150)not null, 
    autor varchar(100)not null, 
    edicion int, 
    anio int,
    sinopsis text,
    idUbicacion int not null, 
    stock int not null, 
    foreign key (idUbicacion) references UBICACION(id) 
);

CREATE TABLE USUARIO(
	id int primary key auto_increment, 
    correo varchar(100) unique not null,  -- username
    contrasenia varchar(64)not null, -- SHA2,
    nombre varchar(100)not null, 
    telefono varbinary(255) not null, -- AESENCRYPT 
    direccion varbinary(255) not null, -- AESENCRYPT 
    rol enum ('administrador', 'empleado', 'lector')not null, 
    activo bool default true not null
);

CREATE TABLE PRESTAMO(
	folio int primary key auto_increment, 
    idEmpleado int not null, 
    idLector int not null, 
    fechaSalida datetime default current_timestamp, 
    fechaLimiteDevolucion datetime not null, 
    foreign key (idEmpleado) references USUARIO(id),
    foreign key (idLector) references USUARIO(id)
);

CREATE TABLE DETALLES_PRESTAMO(
	idPrestamo int not null, 
    idLibro int not null, 
    cantidad int not null, 
    fechaRealDevolucion datetime,
    estado enum ('prestado','devuelto') default 'prestado', 
    foreign key (idPrestamo) references PRESTAMO(folio),
    foreign key (idLibro) references LIBRO(id),
    primary key (idPrestamo, idLibro)
);

CREATE TABLE AUDITORIA(
	id int primary key auto_increment, 
    tablaAfectada varchar(50) not null,
    tipoDeOperacion enum('Insercion', 'Eliminacion', 'Edicion')not null,
    fecha_hora datetime default current_timestamp,
    idUsuario int, -- no entendi por que aqui no puedo poner not null
    informacionAnterior text,
    informacionNueva text,
    foreign key (idUsuario) references USUARIO(id)
);

-- INSERCION DE DATOS DE PRUEBA 

INSERT INTO UBICACION (estante, fila) VALUES 
(1, 1),
(1, 2),
(2, 1),
(2, 2);

INSERT INTO LIBRO (codigo, titulo, autor, edicion, anio, sinopsis, idUbicacion, stock) VALUES
('9788497592208', 'Cien años de soledad', 'Gabriel García Márquez', 1, 1967, 'Historia de la familia Buendía en Macondo.', 1, 4),
('9786073193894', 'El principito', 'Antoine de Saint-Exupéry', 3, 1943, 'Relato sobre un pequeño príncipe y sus viajes por distintos planetas.', 1, 2),
('9788499890944', '1984', 'George Orwell', 2, 1949, 'Novela sobre vigilancia estatal y control social.', 2, 5),
('9780132350884', 'Clean Code', 'Robert C. Martin', 1, 2008, 'Guía de buenas prácticas para escribir código legible y mantenible.', 3, 1);

INSERT INTO USUARIO (correo, contrasenia, nombre, telefono, direccion, rol, activo) VALUES
('admin@biblioteca.com', SHA2('admin123', 256), 'Karla Fuentes', AES_ENCRYPT('4451001122', 'biblioteca_2026'), AES_ENCRYPT('Calle Hidalgo 120, Centro', 'biblioteca_2026'), 'administrador', TRUE),
('empleado@biblioteca.com', SHA2('empleado123', 256), 'Daniel López', AES_ENCRYPT('4451003344', 'biblioteca_2026'), AES_ENCRYPT('Av. Juárez 45, Moroleón', 'biblioteca_2026'), 'empleado', TRUE),
('lector@correo.com', SHA2('lector123', 256), 'Ana Ruiz', AES_ENCRYPT('4451005566', 'biblioteca_2026'), AES_ENCRYPT('Morelos 88, Uriangato', 'biblioteca_2026'), 'lector', TRUE),
('juan@correo.com', SHA2('lector456', 256), 'Juan Pérez', AES_ENCRYPT('4451007788', 'biblioteca_2026'), AES_ENCRYPT('Zaragoza 14, Moroleón', 'biblioteca_2026'), 'lector', TRUE);

INSERT INTO PRESTAMO (idEmpleado, idLector, fechaSalida, fechaLimiteDevolucion) VALUES
(2, 3, '2026-11-01 10:00:00', '2026-11-08 18:00:00'),
(2, 4, '2026-11-20 12:30:00', '2026-11-27 18:00:00'),
(1, 3, '2026-10-15 09:15:00', '2026-10-22 18:00:00');

INSERT INTO DETALLES_PRESTAMO (idPrestamo, idLibro, cantidad, fechaRealDevolucion, estado) VALUES
(1, 1, 1, NULL, 'prestado'),
(1, 2, 1, '2026-11-07 16:00:00', 'devuelto'),
(2, 3, 1, NULL, 'prestado'),
(3, 1, 1, '2026-10-25 14:00:00', 'devuelto');

-- FUNCIONES ALMACENADAS 

DELIMITER $$
CREATE FUNCTION calcular_dias_retraso(f_idPrestamo int, f_idLibro int)
returns int 
READS SQL DATA
BEGIN
	DECLARE dias int;
    
	select datediff(IFNULL(dp.fechaRealDevolucion, current_timestamp), p.fechaLimiteDevolucion) INTO dias
	from detalles_prestamo dp join prestamo p on (dp.idprestamo = p.folio)
	where f_idPrestamo = dp.idPrestamo and f_idLibro = dp.idLibro;
    
    if dias < 0 or dias is null then 
		set dias = 0;
	end if;
    
    RETURN dias;
END $$
DELIMITER ; 

DELIMITER $$
CREATE FUNCTION hay_stock(f_idLibro int, cantidad int)
returns bool
READS SQL DATA
BEGIN
	DECLARE haystock bool;
    DECLARE stockactual int;
    
	select l.stock INTO stockactual
    from libro l
    where l.id = f_idLibro;
    
    if stockactual >= cantidad then
		set haystock = true;
	else 
		set haystock = false;
	end if;
    
    RETURN haystock;
END $$
DELIMITER ; 

-- TRIGGERS DE VALIDACION 
DELIMITER $$
CREATE TRIGGER validar_stock
BEFORE INSERT ON detalles_prestamo
FOR EACH ROW
BEGIN
	declare v_titulo varchar(150);
    declare v_mensaje varchar(128);
    
    if(new.cantidad <= 0) then
    SIGNAL SQLSTATE '45000'
		SET MESSAGE_TEXT ='La cantidad a prestar debe ser mayor a cero';
	END IF;
    
	IF hay_stock(NEW.idLibro, NEW.cantidad) = false then
		select titulo into v_titulo
        from libro where id=new.idLibro; 
        
        set v_mensaje = left(concat('Stock insuficiente para: ', ifnull(v_titulo, 'Libro Inexistente') ),128);
		SIGNAL SQLSTATE '45000'
		SET MESSAGE_TEXT =v_mensaje;
	END IF;
END $$
DELIMITER ;

DELIMITER $$
CREATE TRIGGER ValidarInsertLibro
BEFORE INSERT ON libro
FOR EACH ROW
BEGIN
    IF NEW.Stock<0 THEN
		SIGNAL SQLSTATE '45000'
		SET MESSAGE_TEXT ='La cantidad disponible no puede ser negativa';
	END IF;
    IF trim(new.codigo) IS NULL OR length(trim(NEW.codigo)) = 0  THEN
		SIGNAL SQLSTATE '45000'
		SET MESSAGE_TEXT ='El codigo no puede estar vacio';
	END IF;
    IF trim(new.titulo) IS NULL OR length(trim(NEW.titulo)) = 0  THEN
		SIGNAL SQLSTATE '45000'
		SET MESSAGE_TEXT ='El titulo no puede estar vacio';
	END IF;
    IF trim(new.autor) IS NULL OR length(trim(NEW.autor)) = 0  THEN
		SIGNAL SQLSTATE '45000'
		SET MESSAGE_TEXT ='El nombre del autor no puede estar vacio';
	END IF;
END $$
DELIMITER ;

DELIMITER $$
CREATE TRIGGER ValidarUpdateLibro
BEFORE UPDATE ON libro
FOR EACH ROW
BEGIN
    IF NEW.Stock<0 THEN
		SIGNAL SQLSTATE '45000'
		SET MESSAGE_TEXT ='La cantidad disponible no puede ser negativa';
	END IF;
    IF trim(new.codigo) IS NULL OR length(trim(NEW.codigo)) = 0  THEN
		SIGNAL SQLSTATE '45000'
		SET MESSAGE_TEXT ='El codigo no puede estar vacio';
	END IF;
    IF trim(new.titulo) IS NULL OR length(trim(NEW.titulo)) = 0  THEN
		SIGNAL SQLSTATE '45000'
		SET MESSAGE_TEXT ='El titulo no puede estar vacio';
	END IF;
    IF trim(new.autor) IS NULL OR length(trim(NEW.autor)) = 0  THEN
		SIGNAL SQLSTATE '45000'
		SET MESSAGE_TEXT ='El nombre del autor no puede estar vacio';
	END IF;
END $$
DELIMITER ;

-- TRIGGERS DE AUDITORIA

DELIMITER $$ 
CREATE TRIGGER RegistrarAuditoriaUpdateLibro		
AFTER UPDATE ON libro
FOR EACH ROW
BEGIN
    INSERT INTO AUDITORIA (tablaAfectada, tipoDeOperacion, idUsuario, informacionAnterior, informacionNueva)
    VALUES (
        'libro',
        'Edicion',
        @usuario_actual,
        CONCAT(
            'ID: ', OLD.id,
            ' | Codigo: ', OLD.codigo,
            ' | Titulo: ', OLD.titulo,
            ' | Autor: ', OLD.autor,
            ' | Edicion: ', IFNULL(OLD.edicion, 'N/A'),
            ' | Anio: ', IFNULL(OLD.anio, 'N/A'),
            ' | Sinopsis: ', IFNULL(OLD.sinopsis, 'N/A'),
            ' | Ubicacion: ', OLD.idUbicacion,
            ' | Stock: ', OLD.stock
        ),
        CONCAT(
            'ID: ', NEW.id,
            ' | Codigo: ', NEW.codigo,
            ' | Titulo: ', NEW.titulo,
            ' | Autor: ', NEW.autor,
            ' | Edicion: ', IFNULL(NEW.edicion, 'N/A'),
            ' | Anio: ', IFNULL(NEW.anio, 'N/A'),
            ' | Sinopsis: ', IFNULL(NEW.sinopsis, 'N/A'),
            ' | Ubicacion: ', NEW.idUbicacion,
            ' | Stock: ', NEW.stock
        )
    );
END $$ 
DELIMITER ;

DELIMITER $$ 
CREATE TRIGGER RegistrarAuditoriaDeleteLibro		
AFTER DELETE ON libro
FOR EACH ROW
BEGIN
    INSERT INTO AUDITORIA (tablaAfectada, tipoDeOperacion, idUsuario, informacionAnterior, informacionNueva)
    VALUES (
        'libro',
        'Eliminacion',
        @usuario_actual,
        CONCAT(
            'ID: ', OLD.id,
            ' | Codigo: ', OLD.codigo,
            ' | Titulo: ', OLD.titulo,
            ' | Autor: ', OLD.autor,
            ' | Edicion: ', IFNULL(OLD.edicion, 'N/A'),
            ' | Anio: ', IFNULL(OLD.anio, 'N/A'),
            ' | Sinopsis: ', IFNULL(OLD.sinopsis, 'N/A'),
            ' | Ubicacion: ', OLD.idUbicacion,
            ' | Stock: ', OLD.stock
        ),
        null
    );
END $$ 
DELIMITER ;

DELIMITER $$ 
CREATE TRIGGER RegistrarAuditoriaUpdateUsuario		
AFTER UPDATE ON Usuario
FOR EACH ROW
BEGIN
    INSERT INTO AUDITORIA (tablaAfectada, tipoDeOperacion, idUsuario, informacionAnterior, informacionNueva)
    VALUES (
        'usuario',
        'Edicion',
        @usuario_actual,
        CONCAT(
            'ID: ', OLD.id,
            ' | Correo: ', OLD.correo,
            ' | Nombre: ', OLD.nombre,
            ' | Rol: ', OLD.rol,
            ' | Activo: ', OLD.activo
        ),
        CONCAT(
            'ID: ', NEW.id,
            ' | Correo: ', NEW.correo,
            ' | Nombre: ', NEW.nombre,
            ' | Rol: ', NEW.rol,
            ' | Activo: ', NEW.activo
        )
    );
END $$ 
DELIMITER ;

-- PROCEDIMIENTOS ALMACENADOS 

DELIMITER // 
CREATE PROCEDURE registrar_prestamo(
IN p_folio_existente INT,
IN p_idEmpleado INT,
IN p_idLector INT, 
IN p_fechaLimiteDevolucion datetime,
IN p_idLibro INT, 
IN p_cantidad INT,
OUT p_folio_generado int
)
BEGIN
	DECLARE empleado_existe INT DEFAULT 0;
    DECLARE lector_existe INT DEFAULT 0;
    
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
    
    SELECT COUNT(*) INTO empleado_existe
    FROM usuario 
    WHERE id = p_idempleado and (rol = 'empleado' or rol = 'administrador') and activo = true;
    
	SELECT COUNT(*) INTO lector_existe
    FROM usuario 
    WHERE id = p_idLector and rol = 'lector' and activo=true;
    
    IF empleado_existe = 0 OR lector_existe = 0 THEN
		SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Empleado o lector no valido o inactivo';
	END IF;

	START TRANSACTION; 
	
    IF p_folio_existente IS NULL OR p_folio_existente = 0 then 
		INSERT INTO PRESTAMO (idEmpleado, idLector, fechaSalida, fechaLimiteDevolucion) VALUES(
			p_idEmpleado, p_idLector, current_timestamp(), p_fechaLimiteDevolucion
		);
    
		SET p_folio_generado = last_insert_id();
	ELSE 
		SET p_folio_generado = p_folio_existente;
	END IF;
	
	INSERT INTO detalles_prestamo (idPrestamo, idLibro, cantidad) VALUES(-- aqui como le hago para insertar el id prestamo? tengo que hacer una variable y un select?
		p_folio_generado, p_idLibro, p_cantidad
	);
	
	UPDATE libro
    SET stock = stock-p_cantidad 
	WHERE id = p_idLibro;
	
	COMMIT;
END //

DELIMITER ;

DELIMITER // 
CREATE PROCEDURE registrar_devolucion(
IN p_folio INT,
IN p_idLibro INT, 
OUT p_dias_retraso INT
)
BEGIN
	DECLARE prestamo_existe INT DEFAULT 0;
    DECLARE cantidad_prestada INT DEFAULT 0;
    
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
    
    SELECT COUNT(*) INTO prestamo_existe
    FROM detalles_prestamo 
    WHERE idPrestamo = p_folio and idLibro = p_idLibro and estado = 'prestado';
    
    IF prestamo_existe = 0 THEN
		SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'El prestamo no existe o el libro ya fue devuelto';
	END IF;
    
    select cantidad into cantidad_prestada
    from detalles_prestamo 
    WHERE idPrestamo = p_folio and idLibro = p_idLibro;

	START TRANSACTION; 
    
    UPDATE libro
    SET stock = stock+cantidad_prestada
	WHERE id = p_idLibro;

	UPDATE detalles_prestamo 
	SET estado = 'devuelto',
		fechaRealDevolucion = current_timestamp()
	WHERE idPrestamo = p_folio and idLibro = p_idLibro;

	SET p_dias_retraso = calcular_dias_retraso(p_folio, p_idLibro);

	COMMIT;
END //
DELIMITER ;

DELIMITER // 
CREATE PROCEDURE escanear_alta_libro(
IN p_codigo varchar(80),
IN p_titulo varchar(150), 
IN p_autor varchar(100),
IN p_edicion INT, 
IN p_anio INT,
IN p_sinopsis TEXT,
IN p_ubicacion INT,
OUT p_id_generado int
)
BEGIN 
	DECLARE v_id_existente INT DEFAULT NULL;
    
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
    
    SELECT id INTO v_id_existente
    FROM libro
    WHERE codigo = TRIM(p_codigo)
    LIMIT 1;

	START TRANSACTION; 
	
    IF v_id_existente IS NULL then 
		INSERT INTO LIBRO (codigo,titulo,autor,edicion,anio,sinopsis,idUbicacion,stock) VALUES( 
			trim(p_codigo), p_titulo, p_autor, p_edicion, p_anio, p_sinopsis, p_ubicacion,1
		);
        
		SET p_id_generado = last_insert_id();
	ELSE 
        UPDATE LIBRO 
        SET stock=stock+1
        where id=v_id_existente;
        
        SET p_id_generado = p_id_existente;
	END IF;
    
	COMMIT;
END //
DELIMITER ;

-- CONSULTAS PARA REPORTES

SELECT l.Codigo,l.Titulo,l.Autor, u.Estante, u.Fila, sum(dp.cantidad) as TotalEjemplaresPrestados
from libro l join ubicacion u on (l.idubicacion = u.id)
join detalles_prestamo dp on (dp.idLibro = l.id)
group by l.Codigo,l.Titulo,l.Autor, u.Estante, u.Fila
order by TotalEjemplaresPrestados desc;

SELECT p.folio, u.nombre, CAST(aes_decrypt(u.telefono, 'biblioteca_2026') AS CHAR) as Telefono, l.titulo, p.fechaLimiteDevolucion,
calcular_dias_retraso(dp.idPrestamo, dp.idLibro) as DiasRetraso, dp.Cantidad
from prestamo p join detalles_prestamo dp on (dp.idPrestamo = p.folio)
join libro l on (l.id = dp.idLibro) 
join usuario u on (p.idLector = u.id)
where dp.estado = 'prestado' and p.fechaLimiteDevolucion < current_timestamp()
order by diasretraso desc;

-- CREACION DE USUARIOS Y PERMISOS 

CREATE USER 'biblio_admin'@'localhost' IDENTIFIED BY 'AdminBiblio_2026!';
CREATE USER 'biblio_empleado'@'localhost' IDENTIFIED BY 'EmpBiblio_2026!';
CREATE USER 'biblio_lector'@'localhost' IDENTIFIED BY 'LectorBiblio_2026!';

GRANT SELECT, INSERT, UPDATE, DELETE, EXECUTE, SHOW VIEW ON BIBLIOTECA.* TO 'biblio_admin'@'localhost';

GRANT SELECT ON BIBLIOTECA.* TO 'biblio_empleado'@'localhost';
GRANT INSERT, UPDATE ON BIBLIOTECA.libro TO 'biblio_empleado'@'localhost';
GRANT INSERT, UPDATE ON BIBLIOTECA.ubicacion TO 'biblio_empleado'@'localhost';
GRANT EXECUTE ON PROCEDURE BIBLIOTECA.registrar_prestamo TO 'biblio_empleado'@'localhost';
GRANT EXECUTE ON PROCEDURE BIBLIOTECA.registrar_devolucion TO 'biblio_empleado'@'localhost';
GRANT EXECUTE ON PROCEDURE BIBLIOTECA.escanear_alta_libro TO 'biblio_empleado'@'localhost';
GRANT EXECUTE ON FUNCTION BIBLIOTECA.calcular_dias_retraso TO 'biblio_empleado'@'localhost';
GRANT EXECUTE ON FUNCTION BIBLIOTECA.hay_stock TO 'biblio_empleado'@'localhost';

GRANT SELECT ON BIBLIOTECA.libro TO 'biblio_lector'@'localhost';
GRANT SELECT ON BIBLIOTECA.ubicacion TO 'biblio_lector'@'localhost';
GRANT SELECT ON BIBLIOTECA.prestamo TO 'biblio_lector'@'localhost';
GRANT SELECT ON BIBLIOTECA.detalles_prestamo TO 'biblio_lector'@'localhost';
GRANT EXECUTE ON FUNCTION BIBLIOTECA.calcular_dias_retraso TO 'biblio_lector'@'localhost';
GRANT EXECUTE ON FUNCTION BIBLIOTECA.hay_stock TO 'biblio_lector'@'localhost';

FLUSH PRIVILEGES;

INSERT INTO usuario (correo, contrasenia, nombre, telefono, direccion, rol, activo) VALUES
('admin@biblioteca.local', SHA2('admin123', 256), 'Administrador General', AES_ENCRYPT('4451000001', 'biblioteca_2026'), AES_ENCRYPT('Centro 10', 'biblioteca_2026'), 'administrador', TRUE),
('empleado@biblioteca.local', SHA2('emp123', 256), 'Empleado Mostrador', AES_ENCRYPT('4451000002', 'biblioteca_2026'), AES_ENCRYPT('Av. Tecnologico 20', 'biblioteca_2026'), 'empleado', TRUE),
('lector@biblioteca.local', SHA2('lector123', 256), 'Lector Prueba', AES_ENCRYPT('4451000003', 'biblioteca_2026'), AES_ENCRYPT('Col. Jardin 30', 'biblioteca_2026'), 'lector', TRUE);