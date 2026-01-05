CREATE TABLE Mietverhaeltnis (
 wohnungsnummer INT,
 ssn INT,
 eigentuemer_id INT,

 PRIMARY KEY (wohnungsnummer, ssn)
);

INSERT INTO Mietverhaeltnis VALUES
                                (1, 1, 1),
                                (2, 2, 2),
                                (3, 3, 3),
                                (4, 4, 4),
                                (5, 5, 5),
                                (6, 6, 6),
                                (7, 7, 7);






