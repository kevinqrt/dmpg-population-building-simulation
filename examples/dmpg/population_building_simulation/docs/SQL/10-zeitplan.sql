CREATE TABLE ZEITPLAN (
    ZEITPLAN_ID INT,
    STARTZEIT   TIME NOT NULL,
    ENDZEIT     TIME NOT NULL,
    DAUER       INT,
    TYP         VARCHAR(50),

    PRIMARY KEY (ZEITPLAN_ID)
);


INSERT INTO Zeitplan (Zeitplan_ID, Startzeit, Endzeit, Dauer, Typ) VALUES
(1, '07:00', '08:00', 60,  'Physiologisch'),  -- 1 Stunde
(2, '18:00', '19:30', 90,  'Freizeit'),       -- 1:30 Stunden
(3, '09:00', '17:00', 480, 'Arbeit'),         -- 8 Stunden
(4, '12:00', '12:30', 30,  'Pause'),          -- 30 Minuten
(5, '20:00', '22:00', 120, 'Freizeit'),       -- 2 Stunden
(6, '06:30', '07:00', 30,  'Physiologisch'),  -- 30 Minuten
(7, '22:30', '23:00', 30,  'Physiologisch');  -- 30 Minuten

