CREATE TABLE Person (
ssn INT CHECK (ssn > 0),
vorname VARCHAR(100) NOT NULL,
nachname VARCHAR(100) NOT NULL,
gesundheit INT CHECK (gesundheit BETWEEN 0 AND 100),
lebensalter INT CHECK (lebensalter >= 0 AND lebensalter < 150),
geburtsdatum DATE,
geschlecht enum ('M', 'W'),

PRIMARY KEY (ssn)
);

INSERT INTO Person VALUES
                       (1, 'Anna', 'Müller', 90, 30, '1994-01-01', 'W'),
                       (2, 'Max', 'Schmidt', 80, 40, '1984-03-12', 'M'),
                       (3, 'Laura', 'Meier', 95, 25, '1999-07-08', 'W'),
                       (4, 'Tom', 'Becker', 70, 50, '1974-05-19', 'M'),
                       (5, 'Julia', 'Klein', 85, 35, '1989-09-23', 'W'),
                       (6, 'Paul', 'Wagner', 60, 60, '1964-11-11', 'M'),
                       (7, 'Alex', 'Neumann', 88, 28, '1996-02-14', 'M');
