CREATE TABLE Grundbeduerfnis (
beduerfnis_id INT,
art enum ('Physiologisch', 'Psychisch'),

primary key (beduerfnis_id)

);

INSERT INTO Grundbeduerfnis VALUES
                                (1, 'Physiologisch'),
                                (2, 'Physiologisch'),
                                (3, 'Psychisch'),
                                (4, 'Psychisch'),
                                (5, 'Psychisch'),
                                (6, 'Physiologisch'),
                                (7, 'Psychisch');
