CREATE TABLE Beduerfnis (
beduerfnis_id INT CHECK (beduerfnis_id > 0),
name VARCHAR(100) NOT NULL CHECK (name not like '^[0-9]+$'),
prioritaet INT CHECK (prioritaet BETWEEN 0 AND 100),

PRIMARY KEY (beduerfnis_id)
);

INSERT INTO Beduerfnis VALUES
                           (1, 'Schlafen', 90),
                           (2, 'Essen', 80),
                           (3, 'Arbeiten', 70),
                           (4, 'Freizeit', 60),
                           (5, 'Sport', 50),
                           (6, 'Shopping', 40),
                           (7, 'Reisen', 30);



