CREATE TABLE BEDUERFNIS (
    BEDUERFNIS_ID   INT,
    BEDUERFNIS_TYP   VARCHAR(50) NOT NULL,
    NAME           VARCHAR(100) NOT NULL,
    PRIORITAET      INT CHECK (PRIORITAET BETWEEN 0 AND 1000),
    DAUER           INT,
    TYP             VARCHAR(50),

    PRIMARY KEY (Beduerfnis_ID)
);


INSERT INTO Beduerfnis (Beduerfnis_ID, Beduerfnis_Typ, Name, Prioritaet, Dauer, Typ) VALUES
(1, 'Grundbedürfnis',   'Schlaf',        900, NULL, 'Physiologisch'),
(2, 'Grundbedürfnis',   'Essen',         800, NULL, 'Physiologisch'),
(3, 'Grundbedürfnis',   'Trinken',       850, NULL, 'Physiologisch'),
(4, 'Komfortbedürfnis', 'Streaming-TV',  300, NULL, 'Freizeit'),
(5, 'Komfortbedürfnis', 'Auto fahren',   400, NULL, 'Bequemlichkeit'),
(6, 'Luxus',            'Urlaub',        200, NULL, 'Freizeit'),
(7, 'Luxus',            'Designer-Kleidung',150, NULL, 'Luxus');



