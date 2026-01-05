CREATE TABLE Wohnung (
wohnungsnummer INT CHECK (wohnungsnummer >= 0),
barrierefrei BOOLEAN,
ausstattung VARCHAR(100),
bewohner_anzahl INT CHECK (bewohner_anzahl BETWEEN 0 AND 50),
gebaeude_id INT NOT NULL,

PRIMARY KEY (wohnungsnummer)
);

INSERT INTO Wohnung VALUES
                        (1, TRUE, 'Standard', 2, 1),
                        (2, FALSE, 'Luxus', 4, 2),
                        (3, TRUE, 'Modern', 3, 3),
                        (4, FALSE, 'Einfach', 1, 4),
                        (5, TRUE, 'Gehoben', 5, 5),
                        (6, FALSE, 'Standard', 2, 6),
                        (7, TRUE, 'Modern', 3, 7);


