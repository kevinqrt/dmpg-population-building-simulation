CREATE TABLE GEBAEUDE (
    GEBAEUDE_ID   INT CHECK ( GEBAEUDE_ID > 0 ),
    ADRESSE_ID    INT NOT NULL REFERENCES ADRESSE(ADRESSE_ID),
    GRUNDFLAECHE  NUMERIC CHECK (GRUNDFLAECHE >= 0),
    ETAGENZAHL  INT CHECK (ETAGENZAHL > 0),
    TYP           VARCHAR(30),

    PRIMARY KEY (GEBAEUDE_ID)
);

INSERT INTO Gebaeude (Gebaeude_ID, Adresse_ID, Grundflaeche, Etagenzahl, Typ) VALUES
(1, 1, 120.5, 3, 'Mehrfamilienhaus'),
(2, 2, 90.0,  2, 'Einfamilienhaus'),
(3, 3, 300.0, 6, 'Mehrfamilienhaus'),
(4, 4, 60.0,  1, 'Einfamilienhaus'),
(5, 5, 220.0, 4, 'Mehrfamilienhaus'),
(6, 6, 150.0, 3, 'Mehrfamilienhaus'),
(7, 7, 80.0,  2, 'Einfamilienhaus');

