ALTER TABLE Adresse
    ADD CONSTRAINT fk_adresse_gebaeude
        FOREIGN KEY (gebaeude_id)
            REFERENCES Gebaeude(gebaeude_id);


ALTER TABLE Gebaeude
    ADD CONSTRAINT fk_gebaeude_koordinaten
        FOREIGN KEY (koordinaten_id)
            REFERENCES Koordinaten(koordinaten_id);


ALTER TABLE Wohnung
    ADD CONSTRAINT fk_wohnung_gebaeude
        FOREIGN KEY (gebaeude_id)
            REFERENCES Gebaeude(gebaeude_id);


ALTER TABLE Bewohner
    ADD CONSTRAINT fk_bewohner_person
        FOREIGN KEY (ssn)
            REFERENCES Person(ssn);


ALTER TABLE Privateigentuemer
    ADD CONSTRAINT fk_privateigentuemer_person
        FOREIGN KEY (ssn)
            REFERENCES Person(ssn);

ALTER TABLE Privateigentuemer
    ADD CONSTRAINT fk_privateigentuemer_eigentuemer
        FOREIGN KEY (eigentuemer_id)
            REFERENCES Eigentuemer(eigentuemer_id);

ALTER TABLE Gewerbeeigentuemer
    ADD CONSTRAINT fk_gewerbeeigentuemer_eigentuemer
        FOREIGN KEY (eigentuemer_id)
            REFERENCES Eigentuemer(eigentuemer_id);


ALTER TABLE Mietverhaeltnis
    ADD CONSTRAINT fk_mietverhaeltnis_wohnung
        FOREIGN KEY (wohnungsnummer)
            REFERENCES Wohnung(wohnungsnummer);

ALTER TABLE Mietverhaeltnis
    ADD CONSTRAINT fk_mietverhaeltnis_bewohner
        FOREIGN KEY (ssn)
            REFERENCES Bewohner(ssn);

ALTER TABLE Mietverhaeltnis
    ADD CONSTRAINT fk_mietverhaeltnis_eigentuemer
        FOREIGN KEY (eigentuemer_id)
            REFERENCES Eigentuemer(eigentuemer_id);


ALTER TABLE Personenzeitplan
    ADD CONSTRAINT fk_personenzeitplan_zeitplan
        FOREIGN KEY (zeitplan_id)
            REFERENCES Zeitplan(zeitplan_id);

ALTER TABLE Personenzeitplan
    ADD CONSTRAINT fk_personenzeitplan_person
        FOREIGN KEY (ssn)
            REFERENCES Person(ssn);

ALTER TABLE Grundbeduerfnis
    ADD CONSTRAINT fk_grundbeduerfnis_beduerfnis
        FOREIGN KEY (beduerfnis_id)
            REFERENCES Beduerfnis(beduerfnis_id);

ALTER TABLE Komfortbeduerfnis
    ADD CONSTRAINT fk_komfortbeduerfnis_beduerfnis
        FOREIGN KEY (beduerfnis_id)
            REFERENCES Beduerfnis(beduerfnis_id);

ALTER TABLE Beduerfnis_Konkurrenz
    ADD CONSTRAINT fk_beduerfnis_konkurrenz_a
        FOREIGN KEY (beduerfnis_a)
            REFERENCES Beduerfnis(beduerfnis_id);

ALTER TABLE Beduerfnis_Konkurrenz
    ADD CONSTRAINT fk_beduerfnis_konkurrenz_b
        FOREIGN KEY (beduerfnis_b)
            REFERENCES Beduerfnis(beduerfnis_id);


ALTER TABLE Ziel
    ADD CONSTRAINT fk_ziel_koordinaten
        FOREIGN KEY (koordinaten_id)
            REFERENCES Koordinaten(koordinaten_id);

ALTER TABLE Aktivitaet
    ADD CONSTRAINT fk_aktivitaet_ziel
        FOREIGN KEY (ziel_id)
            REFERENCES Ziel(ziel_id);
