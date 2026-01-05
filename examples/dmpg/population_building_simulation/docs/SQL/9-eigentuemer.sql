CREATE TABLE Eigentuemer (
eigentuemer_id INT CHECK (eigentuemer_id > 0),
wohnungen_anzahl INT CHECK (wohnungen_anzahl > 0),

PRIMARY KEY (eigentuemer_id)
);

INSERT INTO Eigentuemer VALUES
                            (1, 2),
                            (2, 3),
                            (3, 1),
                            (4, 4),
                            (5, 2),
                            (6, 5),
                            (7, 1);
