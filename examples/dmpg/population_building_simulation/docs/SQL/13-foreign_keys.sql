/* Adresse( Koordinaten_ID ) -> Koordinaten( Koordinaten_ID ) */
ALTER TABLE Adresse
    ADD CONSTRAINT fk_adresse_koordinaten
        FOREIGN KEY (Koordinaten_ID)
            REFERENCES Koordinaten (Koordinaten_ID);

/* Gebäude( Adresse_ID ) -> Adresse( Adresse_ID ) */
ALTER TABLE Gebaeude
    ADD CONSTRAINT fk_gebaeude_adresse
        FOREIGN KEY (Adresse_ID)
            REFERENCES Adresse (Adresse_ID);

/* Wohnung( Gebaeude_ID ) -> Gebaeude( Gebaeude_ID ) */
ALTER TABLE Wohnung
    ADD CONSTRAINT fk_wohnung_gebaeude
        FOREIGN KEY (Gebaeude_ID)
            REFERENCES Gebaeude (Gebaeude_ID);

/* Wohnung( Eigentuemer_SSN ) <- Person( SSN )
   Du hast gesagt: von Person(SSN) nach Wohnung(Eigentuemer_SSN),
   d.h. Eigentuemer_SSN in Wohnung ist der FK auf Person.SSN. */
ALTER TABLE Wohnung
    ADD CONSTRAINT fk_wohnung_eigentuemer
        FOREIGN KEY (Eigentuemer_SSN)
            REFERENCES Person (SSN);

/* Mietverhältnis( Wohnungsnummer ) -> Wohnung( Wohnungsnummer ) */
ALTER TABLE Mietverhaeltnis
    ADD CONSTRAINT fk_mietverhaeltnis_wohnung
        FOREIGN KEY (Wohnungsnummer)
            REFERENCES Wohnung (Wohnungsnummer);

/* Mietverhältnis( SSN ) -> Person( SSN ) */
ALTER TABLE Mietverhaeltnis
    ADD CONSTRAINT fk_mietverhaeltnis_person
        FOREIGN KEY (SSN)
            REFERENCES Person (SSN);

/* Aktivitaet( Adresse_ID ) -> Adresse( Adresse_ID ) */
ALTER TABLE Aktivitaet
    ADD CONSTRAINT fk_aktivitaet_adresse
        FOREIGN KEY (Adresse_ID)
            REFERENCES Adresse (Adresse_ID);

/* Aktivitaetsadresse( Adresse_ID ) -> Adresse( Adresse_ID ) */
ALTER TABLE Aktivitaetsadresse
    ADD CONSTRAINT fk_aktivitaetsadresse_adresse
        FOREIGN KEY (Adresse_ID)
            REFERENCES Adresse (Adresse_ID);

/* Aktivitaetsadresse( Aktivitaet_ID ) -> Aktivitaet( Aktivitaet_ID ) */
ALTER TABLE Aktivitaetsadresse
    ADD CONSTRAINT fk_aktivitaetsadresse_aktivitaet
        FOREIGN KEY (Aktivitaet_ID)
            REFERENCES Aktivitaet (Aktivitaet_ID);

/* GemachteAktivitaet( SSN ) -> Person( SSN ) */
ALTER TABLE gemachte_aktivitaet
    ADD CONSTRAINT fk_gemachteaktivitaet_person
        FOREIGN KEY (SSN)
            REFERENCES Person (SSN);

/* GemachteAktivitaet( Aktivitaet_ID ) -> Aktivitaet( Aktivitaet_ID ) */
ALTER TABLE gemachte_aktivitaet
    ADD CONSTRAINT fk_gemachteaktivitaet_aktivitaet
        FOREIGN KEY (Aktivitaet_ID)
            REFERENCES Aktivitaet (Aktivitaet_ID);

/* Person( Zeitplan_ID ) -> Zeitplan( Zeitplan_ID ) */

ALTER TABLE Person
    ADD CONSTRAINT fk_person_zeitplan
        FOREIGN KEY (Zeitplan_ID)
            REFERENCES Zeitplan (Zeitplan_ID);

/* Beduerfniszuordnung( SSN ) -> Person( SSN ) */
ALTER TABLE Beduerfniszuordnung
    ADD CONSTRAINT fk_beduerfniszuordnung_person
        FOREIGN KEY (SSN)
            REFERENCES Person (SSN);

/* Beduerfniszuordnung( Beduerfnis_ID ) -> Beduerfnis( Beduerfnis_ID ) */
ALTER TABLE Beduerfniszuordnung
    ADD CONSTRAINT fk_beduerfniszuordnung_beduerfnis
        FOREIGN KEY (Beduerfnis_ID)
            REFERENCES Beduerfnis (Beduerfnis_ID);




