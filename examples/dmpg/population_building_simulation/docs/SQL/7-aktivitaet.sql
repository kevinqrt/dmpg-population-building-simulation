CREATE TABLE AKTIVITAET (
    AKTIVITAET_ID INT,
    ADRESSE_ID    INT REFERENCES ADRESSE(ADRESSE_ID),
    NAME          VARCHAR(100) NOT NULL,

    PRIMARY KEY (Aktivitaet_ID)
);

INSERT INTO Aktivitaet (Aktivitaet_ID, Adresse_ID, Name) VALUES
(1, 1, 'Joggen im Park'),
(2, 2, 'Einkaufen'),
(3, 3, 'Kino'),
(4, 4, 'Fitnessstudio'),
(5, 5, 'Spaziergang'),
(6, 6, 'Restaurantbesuch'),
(7, 7, 'Schwimmen');
