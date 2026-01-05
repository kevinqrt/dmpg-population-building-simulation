CREATE TABLE Beduerfnis_Konkurrenz (
beduerfnis_a INT,
beduerfnis_b INT,

PRIMARY KEY (beduerfnis_a, beduerfnis_b),
CHECK (beduerfnis_a <> beduerfnis_b)
);

INSERT INTO Beduerfnis_Konkurrenz VALUES
                                      (1, 2),
                                      (2, 3),
                                      (3, 4),
                                      (4, 5),
                                      (5, 6),
                                      (6, 7),
                                      (7, 1);
