--
-- PostgreSQL database dump
--

-- Dumped from database version 13.14 (Debian 13.14-0+deb11u1)
-- Dumped by pg_dump version 13.14 (Debian 13.14-0+deb11u1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

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
-- PostgreSQL database dump complete
--
