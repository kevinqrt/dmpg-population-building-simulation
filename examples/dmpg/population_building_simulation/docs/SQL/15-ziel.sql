CREATE TABLE Ziel (
ziel_id INT CHECK (ziel_id > 0),
name VARCHAR(100) NOT NULL,
koordinaten_id INT NOT NULL,

PRIMARY KEY (ziel_id)

);

INSERT INTO Ziel VALUES
                     (1, 'Arbeit', 1),
                     (2, 'Zuhause', 2),
                     (3, 'Fitnessstudio', 3),
                     (4, 'Park', 4),
                     (5, 'Einkaufszentrum', 5),
                     (6, 'Restaurant', 6),
                     (7, 'Kino', 7);
