CREATE TABLE Komfortbeduerfnis (
beduerfnis_id INT,
kategorie ENUM ('Luxus', 'Bequemlichkeit', 'Freizeit'),

primary key (beduerfnis_id)
);

INSERT INTO Komfortbeduerfnis VALUES
                                  (1, 'Bequemlichkeit'),
                                  (2, 'Bequemlichkeit'),
                                  (3, 'Luxus'),
                                  (4, 'Freizeit'),
                                  (5, 'Freizeit'),
                                  (6, 'Luxus'),
                                  (7, 'Bequemlichkeit');

