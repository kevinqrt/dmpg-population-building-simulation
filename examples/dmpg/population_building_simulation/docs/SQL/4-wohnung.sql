CREATE TABLE WOHNUNG (
    WOHNUNGSNUMMER   INT CHECK ( WOHNUNGSNUMMER > 0 ),
    EIGENTUEMER_SSN  INT,
    GEBAEUDE_ID      INT NOT NULL,
    BARRIEREFREI     BOOLEAN,
    AUSSTATTUNG      VARCHAR(100),
    BEWOHNER_ANZAHL  INT CHECK (BEWOHNER_ANZAHL >= 0),

    PRIMARY KEY (WOHNUNGSNUMMER)
);

INSERT INTO Wohnung (Wohnungsnummer, Eigentuemer_SSN, Gebaeude_ID, Barrierefrei, Ausstattung, Bewohner_Anzahl) VALUES
(1, 1001, 1, TRUE,  'Standard', 2),
(2, 1002, 1, FALSE, 'Luxus',    3),
(3, 1003, 2, TRUE,  'Basis',    1),
(4, 1004, 3, FALSE, 'Standard', 4),
(5, 1005, 4, TRUE,  'Luxus',    2),
(6, 1006, 5, FALSE, 'Basis',    1),
(7, 1007, 6, TRUE,  'Standard', 3);



