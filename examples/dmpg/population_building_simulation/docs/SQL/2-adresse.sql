CREATE TABLE Adresse (
adresse_id INT CHECK (adresse_id > 0),
strasse VARCHAR(255) NOT NULL,
stadt VARCHAR(255) NOT NULL,
hausnummer int,
plz INT CHECK (plz BETWEEN 10000 AND 99999),
hausnummer_zusatz CHAR(1),
gebaeude_id INT NOT NULL,

PRIMARY KEY (adresse_id)
);

INSERT INTO Adresse VALUES
                        (1, 'Hauptstraße', 'Berlin', 12, 10115, 'a', 1),
                        (2, 'Bahnhofstraße', 'München', 5, 80331, NULL, 2),
                        (3, 'Zeil', 'Frankfurt', 98, 60313, NULL, 3),
                        (4, 'Alsterweg', 'Hamburg', 7, 20095, 'b', 4),
                        (5, 'Königsallee', 'Düsseldorf', 1, 40212, NULL, 5),
                        (6, 'Marktplatz', 'Karlsruhe', 22, 76133, NULL, 6),
                        (7, 'Lister Meile', 'Hannover', 8, 30161, NULL, 7);






