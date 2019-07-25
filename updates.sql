
 
 UPDATE matches SET the_geom = (SELECT MakePoint('LINESTRING('||o.lon||' '||o.lat||', '||n.lon_Steig||' '||n.lat_Steig||')', 4326)
 FROM osm_stops o, haltestellen n
 WHERE o.node_id = m.osm_id AND m.ifopt_id = n.globaleID_Steig AND n.lat_Steig IS NOT NULL);

 CREATE TABLE matches AS
SELECT vice_versa_best.*
  FROM (SELECT ifopt_id, max(rating) rating FROM candidates GROUP BY ifopt_id) ifopt_best,
		   (SELECT osm_id, max(rating) rating FROM candidates GROUP BY osm_id) osm_best,
		   candidates vice_versa_best
  WHERE ifopt_best.ifopt_id = vice_versa_best.ifopt_id
      AND ifopt_best.rating = vice_versa_best.rating
	  AND osm_best.rating = vice_versa_best.rating
	  AND osm_best.osm_id = vice_versa_best.osm_id;
	  
SELECT count(*) from matches where the_geom is not null;
	  
-- Doppelte IFOPT IDs für Steige	  
SELECT ref_key,  COUNT(*) from osm_stops WHERE ref IS NOT NULL GROUP BY ref_key HAVING COUNT(*) > 1 AND LENGTH(ref_key) - LENGTH(REPLACE(ref_key, ':', ''))= 4;

-- Statistik
SELECT 'OSM Stops gesamt', COUNT(*) from osm_stops
UNION
SELECT 'OSM Stops ('||IFNULL(type, 'ohne Angabe')||')', COUNT(*) from osm_stops GROUP BY type
UNION
SELECT 'Stops ohne Name', COUNT(*) from osm_stops WHERE name IS NULL
;

SELECT o.name, n.Haltestelle, n.Haltestelle_lang, m.*, o.*, n.* FROM matches m, osm_stops o, haltestellen n
WHERE o.node_id = m.osm_id AND m.ifopt_id=n.globaleID_Steig
AND name_distance < 1;

SELECT 'Haltestellen-Namen mit Abkürzungen', COUNT(*) FROM (SELECT DISTINCT Haltestelle, Haltestelle_lang FROM haltestellen WHERE (LENGTH(Haltestelle)-LENGTH(REPLACE(Haltestelle, '.','')) > 0);


SELECT * FROM osm_stops WHERE node_id NOT IN (SELECT osm_id FROM candidates);

SELECT count(*) from osm_stops where the_geom is  not null;

SELECT network, COUNT(*) FROM osm_stops WHERE node_id NOT IN (SELECT osm_id FROM candidates) GROUP BY network ORDER BY COUNT(*) DESC;

SELECT 'Halltestellen ohne Koordinate', COUNT(*) FROM haltestellen WHERE lat IS NULL 
UNION
SELECT 'Steige ohne Koordinate', COUNT(*) FROM haltestellen WHERE globaleID_Steig IS NOT NULL AND lat_Steig IS NULL;

SELECT load_extension('mod_spatialite.dylib');

SELECT 'Bereich-ID der Steig-ID weicht von Bereich-ID ab', COUNT(*) FROM Haltestellen WHERE NOT globaleID_Steig LIKE globaleID_Bereich||'%'
UNION
SELECT 'Halt-ID der Steig-ID weicht von Halt-ID ab', COUNT(*) FROM Haltestellen WHERE NOT globaleID_Steig LIKE globaleID||'%';

CREATE VIEW landkreis_globaleID_typos AS 
SELECT landkreis  FROM (
SELECT DISTINCT landkreis, substr(globaleID,4,5) landkreis_schl FROM Haltestellen WHERE globaleID IS NOT NULL
UNION
SELECT DISTINCT landkreis, substr(globaleID_Steig,4,5) landkreis_schl FROM Haltestellen WHERE globaleID_Steig IS NOT NULL
UNION
SELECT DISTINCT landkreis, substr(globaleID_Bereich,4,5) landkreis_schl FROM Haltestellen WHERE globaleID_Bereich IS NOT NULL )
GROUP BY landkreis HAVING COUNT(*) >1;

SELECT DISTINCT landkreis, substr(globaleID,4,5) landkreis_schl FROM Haltestellen WHERE globaleID IS NOT NULL AND landkreis IN landkreis_globaleID_typos
UNION
SELECT DISTINCT landkreis, substr(globaleID_Steig,4,5) landkreis_schl FROM Haltestellen WHERE globaleID_Steig IS NOT NULL AND landkreis IN landkreis_globaleID_typos
UNION
SELECT DISTINCT landkreis, substr(globaleID_Bereich,4,5) landkreis_schl FROM Haltestellen WHERE globaleID_Bereich IS NOT NULL AND landkreis IN landkreis_globaleID_typos;

DROP VIEW landkreis_globaleID_typos;
CREATE VIEW landkreis_globaleID_typos AS 
SELECT landkreis, landkreis_schl FROM (
SELECT DISTINCT landkreis, substr(globaleID,4,5) landkreis_schl FROM Haltestellen WHERE globaleID IS NOT NULL
UNION
SELECT DISTINCT landkreis, substr(globaleID_Steig,4,5) landkreis_schl FROM Haltestellen WHERE globaleID_Steig IS NOT NULL
UNION
SELECT DISTINCT landkreis, substr(globaleID_Bereich,4,5) landkreis_schl FROM Haltestellen WHERE globaleID_Bereich IS NOT NULL )
GROUP BY landkreis HAVING COUNT(*) >1;

CREATE VIEW landkreis_globaleID_typos AS 
SELECT landkreis, landkreis_schl FROM (
SELECT DISTINCT landkreis, substr(globaleID,4,5) landkreis_schl FROM Haltestellen WHERE globaleID IS NOT NULL
UNION
SELECT DISTINCT landkreis, substr(globaleID_Steig,4,5) landkreis_schl FROM Haltestellen WHERE globaleID_Steig IS NOT NULL
UNION
SELECT DISTINCT landkreis, substr(globaleID_Bereich,4,5) landkreis_schl FROM Haltestellen WHERE globaleID_Bereich IS NOT NULL );
SELECT * FROM landkreis_globaleID_typos WHERE landkreis IN (SELECT landkreis FROM landkreis_globaleID_typos GROUP BY landkreis HAVING COUNT(*) >1);

select abs(lat-lat_Steig)+abs(lon-lon_steig), globaleID_Steig FROM haltestellen where lat IS NOT NULL AND lat_Steig IS NOT NULL ORDER BY abs(lat-lat_Steig)+abs(lon-lon_steig), globaleID_Steig  ;

SELECT * FROM haltestellen WHERE Name_Bereich like '%SEV%';
SELECT * FROM haltestellen WHERE Name_Bereich like '%rsatz%' or Name_Bereich like '%SEV%' or Name_Steig like '%rsatz%'or Name_Steig like '%SEV%';;

select * from successor where pred_id=332571047;
SELECT * FROM osm_stops o where name = 'Am Ochsenwald'; 
SELECT * FROM osm_stops o, successor s,osm_stops so where o.name = 'Am Ochsenwald' and s.pred_id = o.node_id and s.succ_id = so.node_id;
SELECT * FROM Haltestellen where Haltestelle = 'Am Ochsenwald';

select distinct Name_Steig from haltestellen;

Ri Ri. eRtg Rtg Richt Fahrtrichtung Ri- Ri: Richtung Richtg. FR >

select count(*) from candidates;

select count(*) from matches;
delete from matches;

DELETE FROM candidates WHERE (ifopt_id, osm_id) in (
select ifopt_id, osm_id from candidates c, osm_stops o, haltestellen h where c.osm_id=o.node_id and c.ifopt_id = h.globaleID_Steig and o.type='bus' and Name_Steig like 'Gleis%'
)

-- TODO übernehmen
DELETE FROM matches WHERE (ifopt_id, osm_id) in (
select c2.ifopt_id, c2.osm_id from matches c1, matches c2 where c1.osm_id=c2.osm_id and c2.rating < c1.rating
);
CREATE TABLE matches_backup AS SELECT * FROM MATCHES;

DELETE FROM candidates WHERE rating < 0.001;

DELETE FROM matches;
SELECT * FROM CANDIDATES WHERE rating < 0.001 order by name_distance desc;
select * from osm_stops where node_id = 4026625598;

SELECT AddTextColumn('haltestellen','match_state');

SELECT * from haltestellen where globaleID_Steig not in (SELECT ifopt_id FROM matches); 

select h.Haltestelle, h.Haltestelle_lang, o.name, rating, name_distance from matches c, osm_stops o, haltestellen h where c.osm_id=o.node_id and c.ifopt_id = h.globaleID_Steig order by distance desc;

ALTER TABLE haltestellen ADD COLUMN match_state TEXT;
UPDATE haltestellen SET match_state = 'no_x_ride' WHERE Name_Bereich like '%+R%' AND match_state IS NULL;
UPDATE haltestellen SET match_state = 'no_entry' WHERE Name_Bereich like '%ugang%' AND match_state IS NULL;
UPDATE haltestellen SET match_state = 'no_replacement' WHERE (Name_Bereich like '%rsatz%' OR Name_Bereich like '%SEV%' OR Name_Steig like '%rsatz%' OR Name_Steig like '%SEV%' )AND match_state IS NULL;
UPDATE haltestellen SET match_state = 'no_extraterritorial' WHERE HalteTyp like '%Netzbereich%' AND match_state IS NULL;
UPDATE haltestellen SET match_state = 'matched' WHERE globaleID_Steig IN (SELECT ifopt_id FROM matches);

select count(*) from haltestellen;
SELECT * FROM candidates ORDER BY name_distance DESC, ifopt_id

select * from haltestellen where globaleID_Steig like 'de:08117:9001:0:R'; -- Göppingen, Knoten ist Teil der Platform-Linie, die Infos zur Platform trägt...
select * from haltestellen where globaleID_Steig like 'de:08415:29333:1:Q';-- Reutlingen
DROP TABLE haltestellen_unified;
CREATE TABLE haltestellen_unified AS
select Landkreis, Gemeinde, Ortsteil, Haltestelle, Haltestelle_lang, HalteBeschreibung, globaleID, HalteTyp, gueltigAb, gueltigBis, lon, lat, 'Halt' Art , NULL Name_Steig, 
	CASE 
		WHEN Name_Bereich LIKE '%Bus%' THEN 'Bus' 
		WHEN Name_Bereich LIKE '%Bahn%' OR Name_Bereich LIKE '%Gleis%' OR Name_Bereich LIKE '%Zug%' OR Name_Steig LIKE '%Gl%' THEN 'BAHN'
		ELSE NULL
	END Mode, NULL parent, match_state FROM haltestellen where lon_Steig IS NULL AND (match_state IS NULL or match_state='matched')
UNION
select Landkreis, Gemeinde, Ortsteil, Haltestelle, Haltestelle_lang, HalteBeschreibung, globaleID_Steig, HalteTyp, gueltigAb, gueltigBis, lon_Steig, lat_Steig, 'Steig' Art, Name_Steig, 
CASE 
		WHEN Name_Bereich LIKE '%Bus%' THEN 'Bus' 
		WHEN Name_Bereich LIKE '%Bahn%' OR Name_Bereich LIKE '%Gleis%' OR Name_Bereich LIKE '%Zug%' OR Name_Steig LIKE '%Gl%' THEN 'BAHN'
		ELSE NULL
	END Mode, globaleID parent, match_state FROM haltestellen  where lon_Steig IS NOT NULL  AND (match_state IS NULL or match_state='matched')
;

SELECT * FROM haltestellen_unified;
SELECT * FROM haltestellen WHERE globaleID='de:08327:2094' and globaleID_Steig =''
SELECT * FROM candidates;

SELECT DISTINCT Landkreis, substr(globaleId, 1,9) FROM haltestellen_unified;

CREATE INDEX id_idx ON haltestellen_unified(globaleID)
---
-- 
SELECT * FROM haltestellen WHERE Haltestelle ='';
-- QS OSM
-- OSM Stops ohne Namen
SELECT * FROM osm_stops WHERE name IS NULL;
-- OSM Stops ohne Namen und offizielle Halte im Umkreis 60m


