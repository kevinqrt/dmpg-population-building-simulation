CREATE TABLE Person (
    SSN            INT,
    ISTEIGENTUEMER BOOLEAN DEFAULT FALSE,
    ISTBEWOHNER    BOOLEAN DEFAULT FALSE,
    GESUNDHEIT     INT CHECK (GESUNDHEIT BETWEEN 0 AND 100),
    VORNAME        VARCHAR(100) NOT NULL,
    NACHNAME       VARCHAR(100) NOT NULL,
    LEBENSALTER    INT CHECK (LEBENSALTER >= 0 AND LEBENSALTER <= 150),
    GEBURTSDATUM   DATE,
    GESCHLECHT     VARCHAR(20) CHECK (GESCHLECHT IN ('Männlich','Weiblich')),
    ZEITPLAN_ID    INT,

    PRIMARY KEY (SSN)
);


INSERT INTO Person (SSN, istEigentuemer, istBewohner, Gesundheit, Vorname, Nachname,
                    LEBENSALTER, Geburtsdatum, Geschlecht, Zeitplan_ID) VALUES
(1001, TRUE,  TRUE,  90, 'Anna',   'Müller',  35, '1989-01-10', 'Weiblich', 1),
(1002, TRUE,  FALSE, 85, 'Peter',  'Schmidt', 45, '1979-05-20', 'Männlich', 2),
(1003, FALSE, TRUE,  70, 'Lena',   'Klein',   22, '2002-03-15', 'Weiblich', 3),
(1004, TRUE,  TRUE,  60, 'Jonas',  'Fischer', 55, '1969-11-02', 'Männlich', 4),
(1005, TRUE,  FALSE, 95, 'Mara',   'Vogel',   30, '1994-06-18', 'Weiblich', 5),
(1006, FALSE, TRUE,  65, 'Timo',   'Becker',  28, '1996-09-09', 'Männlich', 6),
(1007, FALSE, TRUE,  80, 'Sara',   'Hoffmann',19, '2005-01-25', 'Weiblich', 7);



