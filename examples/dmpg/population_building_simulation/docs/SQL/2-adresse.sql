CREATE OR REPLACE TABLE ADRESSE(
     ADRESSE_ID        INT CHECK ( ADRESSE_ID > 0 ),
     Koordinaten_ID    INT REFERENCES KOORDINATEN(Koordinaten_ID),
     Ort               VARCHAR(100) NOT NULL,
     Hausnummer        VARCHAR(10),
     PLZ               INT,
     Hausnummer_zusatz VARCHAR(10),

    PRIMARY KEY (ADRESSE_ID)
);

INSERT INTO Adresse (Adresse_ID, Koordinaten_ID, Ort, Hausnummer, PLZ, Hausnummer_zusatz) VALUES
(1, 1, 'Frankfurt', '10', 60311, NULL),
(2, 2, 'München',   '5A', 80331, 'A'),
(3, 3, 'Berlin',    '20', 10117, NULL),
(4, 4, 'Hamburg',   '7',  20095, NULL),
(5, 5, 'Dresden',   '12', 01067, NULL),
(6, 6, 'Karlsruhe', '3B', 76131, 'B'),
(7, 7, 'Freiburg',  '9',  79098, NULL);


