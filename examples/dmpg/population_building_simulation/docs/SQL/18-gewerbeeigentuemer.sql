CREATE TABLE Gewerbeeigentuemer (
gewerbe_id INT CHECK (gewerbe_id > 0),
ust_id INT CHECK (ust_id > 0),
firmenname VARCHAR(255),
eigentuemer_id INT NOT NULL,

PRIMARY KEY (gewerbe_id)
);

INSERT INTO Gewerbeeigentuemer VALUES
                                   (1, 10001, 'Alpha GmbH', 1),
                                   (2, 10002, 'Beta AG', 2),
                                   (3, 10003, 'Gamma KG', 3),
                                   (4, 10004, 'Delta GmbH', 4),
                                   (5, 10005, 'Epsilon AG', 5),
                                   (6, 10006, 'Zeta GmbH', 6),
                                   (7, 10007, 'Eta AG', 7);
