CREATE TABLE Gebaeude (
gebaeude_id INT CHECK (gebaeude_id > 0),
grundflaeche FLOAT CHECK (grundflaeche >= 0),
etagenanzahl INT CHECK (etagenanzahl > 0),
typ ENUM ('Einfamilienhaus', 'Mehrfamilienhaus', 'Unbestimmt'),
koordinaten_id INT,

PRIMARY KEY (gebaeude_id)

);

INSERT INTO Gebaeude VALUES
                         (1, 120.5, 2, 'Einfamilienhaus', 1),
                         (2, 450.0, 5, 'Mehrfamilienhaus', 2),
                         (3, 300.0, 4, 'Mehrfamilienhaus', 3),
                         (4, 90.0, 1, 'Einfamilienhaus', 4),
                         (5, 600.0, 6, 'Mehrfamilienhaus', 5),
                         (6, 200.0, 3, 'Unbestimmt', 6),
                         (7, 350.0, 4, 'Mehrfamilienhaus', 7);



