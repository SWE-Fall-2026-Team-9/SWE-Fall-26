--
-- PostgreSQL database dump
--

\restrict BB8ul71y9ZtLPsDBeiivE1N8rw1vWfC1Qdqbqee5q081Vci4T0Vy0DngK4Ffa6n

-- Dumped from database version 13.16 (Debian 13.16-0+deb11u1)
-- Dumped by pg_dump version 17.11 (Debian 17.11-0+deb13u1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: postgres
--

-- *not* creating schema, since initdb creates it


ALTER SCHEMA public OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: players; Type: TABLE; Schema: public; Owner: student
--

CREATE TABLE public.players (
    id integer,
    codename character varying(255)
);


ALTER TABLE public.players OWNER TO student;

--
-- Data for Name: players; Type: TABLE DATA; Schema: public; Owner: student
--

COPY public.players (id, codename) FROM stdin;
1	Opus
\.


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE USAGE ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--

\unrestrict BB8ul71y9ZtLPsDBeiivE1N8rw1vWfC1Qdqbqee5q081Vci4T0Vy0DngK4Ffa6n

