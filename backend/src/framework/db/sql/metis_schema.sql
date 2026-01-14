--
-- PostgreSQL database dump
--

-- Dumped from database version 17.4 (Debian 17.4-1.pgdg120+2)
-- Dumped by pg_dump version 17.4 (Debian 17.4-1.pgdg120+2)

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

--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: postgres
--

COMMENT ON SCHEMA public IS '';


--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: book; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.book (
    idbook integer NOT NULL,
    title character varying(255) NOT NULL,
    idlanguage integer NOT NULL,
    createdat timestamp without time zone NOT NULL,
    updatedat timestamp without time zone,
    enabled boolean NOT NULL,
    authors character varying(255)[],
    code character varying(255) NOT NULL,
    year integer
);


ALTER TABLE public.book OWNER TO postgres;

--
-- Name: book_idbook_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.book_idbook_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.book_idbook_seq OWNER TO postgres;

--
-- Name: book_idbook_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.book_idbook_seq OWNED BY public.book.idbook;


--
-- Name: chunk; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chunk (
    idchunk integer NOT NULL,
    content text,
    idbook integer NOT NULL,
    idlanguage integer NOT NULL,
    createdat timestamp without time zone NOT NULL,
    updatedat timestamp without time zone,
    enabled boolean NOT NULL,
    idcompetence integer NOT NULL,
    idtopic integer NOT NULL,
    embedding public.halfvec(2560),
    idsubdocument integer
);


ALTER TABLE public.chunk OWNER TO postgres;

--
-- Name: chunk_idchunk_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.chunk_idchunk_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.chunk_idchunk_seq OWNER TO postgres;

--
-- Name: chunk_idchunk_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.chunk_idchunk_seq OWNED BY public.chunk.idchunk;


--
-- Name: competence; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.competence (
    idcompetence integer NOT NULL,
    createdat timestamp without time zone NOT NULL,
    updatedat timestamp without time zone,
    enabled boolean NOT NULL,
    code character varying(255) NOT NULL,
    idtopic integer NOT NULL
);


ALTER TABLE public.competence OWNER TO postgres;

--
-- Name: competence_idcompetence_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.competence_idcompetence_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.competence_idcompetence_seq OWNER TO postgres;

--
-- Name: competence_idcompetence_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.competence_idcompetence_seq OWNED BY public.competence.idcompetence;


--
-- Name: competenceconcept; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.competenceconcept (
    idcompetence integer NOT NULL,
    idconcept integer NOT NULL,
    createdat timestamp without time zone NOT NULL,
    updatedat timestamp without time zone,
    enabled boolean NOT NULL
);


ALTER TABLE public.competenceconcept OWNER TO postgres;

--
-- Name: competencelevel; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.competencelevel (
    idcompetencelevel integer NOT NULL,
    createdat timestamp without time zone NOT NULL,
    updatedat timestamp without time zone,
    enabled boolean NOT NULL,
    code character varying(255) NOT NULL
);


ALTER TABLE public.competencelevel OWNER TO postgres;

--
-- Name: competencelevel_idcompetencelevel_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.competencelevel_idcompetencelevel_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.competencelevel_idcompetencelevel_seq OWNER TO postgres;

--
-- Name: competencelevel_idcompetencelevel_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.competencelevel_idcompetencelevel_seq OWNED BY public.competencelevel.idcompetencelevel;


--
-- Name: competenceleveltranslation; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.competenceleveltranslation (
    idcompetencelevel integer NOT NULL,
    idlanguage integer NOT NULL,
    name character varying(255) NOT NULL,
    description text
);


ALTER TABLE public.competenceleveltranslation OWNER TO postgres;

--
-- Name: competencetranslation; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.competencetranslation (
    idcompetence integer NOT NULL,
    idlanguage integer NOT NULL,
    name character varying(255) NOT NULL,
    description text
);


ALTER TABLE public.competencetranslation OWNER TO postgres;

--
-- Name: concept; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.concept (
    idconcept integer NOT NULL,
    createdat timestamp without time zone NOT NULL,
    updatedat timestamp without time zone,
    enabled boolean NOT NULL,
    code character varying(255) NOT NULL
);


ALTER TABLE public.concept OWNER TO postgres;

--
-- Name: concept_idconcept_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.concept_idconcept_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.concept_idconcept_seq OWNER TO postgres;

--
-- Name: concept_idconcept_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.concept_idconcept_seq OWNED BY public.concept.idconcept;


--
-- Name: concepttranslation; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.concepttranslation (
    idconcept integer NOT NULL,
    idlanguage integer NOT NULL,
    name character varying(255) NOT NULL,
    description text
);


ALTER TABLE public.concepttranslation OWNER TO postgres;

--
-- Name: language; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.language (
    idlanguage integer NOT NULL,
    name character varying(255) NOT NULL,
    createdat timestamp without time zone NOT NULL,
    updatedat timestamp without time zone,
    enabled boolean NOT NULL,
    code character varying(2) NOT NULL
);


ALTER TABLE public.language OWNER TO postgres;

--
-- Name: language_idlanguage_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.language_idlanguage_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.language_idlanguage_seq OWNER TO postgres;

--
-- Name: language_idlanguage_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.language_idlanguage_seq OWNED BY public.language.idlanguage;


--
-- Name: learningstep; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.learningstep (
    idstep integer NOT NULL,
    createdat timestamp without time zone NOT NULL,
    updatedat timestamp without time zone,
    enabled boolean NOT NULL,
    code character varying(255) NOT NULL
);


ALTER TABLE public.learningstep OWNER TO postgres;

--
-- Name: learningstep_idstep_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.learningstep_idstep_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.learningstep_idstep_seq OWNER TO postgres;

--
-- Name: learningstep_idstep_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.learningstep_idstep_seq OWNED BY public.learningstep.idstep;


--
-- Name: learningsteptranslation; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.learningsteptranslation (
    idstep integer NOT NULL,
    idlanguage integer NOT NULL,
    name character varying(255) NOT NULL,
    description text
);


ALTER TABLE public.learningsteptranslation OWNER TO postgres;

--
-- Name: learningunit; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.learningunit (
    idlearningunit integer NOT NULL,
    idstep integer NOT NULL,
    idconcept integer NOT NULL,
    idcompetencelevel integer NOT NULL,
    createdat timestamp without time zone NOT NULL,
    updatedat timestamp without time zone,
    enabled boolean NOT NULL,
    code character varying(255) NOT NULL
);


ALTER TABLE public.learningunit OWNER TO postgres;

--
-- Name: learningunit_idlearningunit_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.learningunit_idlearningunit_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.learningunit_idlearningunit_seq OWNER TO postgres;

--
-- Name: learningunit_idlearningunit_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.learningunit_idlearningunit_seq OWNED BY public.learningunit.idlearningunit;


--
-- Name: learningunittranslation; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.learningunittranslation (
    idlearningunit integer NOT NULL,
    idlanguage integer NOT NULL,
    learninggoal text,
    task text,
    solution text,
    name text
);


ALTER TABLE public.learningunittranslation OWNER TO postgres;

--
-- Name: subdocument; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.subdocument (
    idsubdocument integer NOT NULL,
    content text,
    idbook integer NOT NULL,
    idlanguage integer NOT NULL,
    idcompetence integer NOT NULL,
    enabled boolean NOT NULL,
    createdat timestamp without time zone NOT NULL,
    updatedat timestamp without time zone,
    idtopic integer NOT NULL
);


ALTER TABLE public.subdocument OWNER TO postgres;

--
-- Name: subdocument_idsubdocument_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.subdocument_idsubdocument_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.subdocument_idsubdocument_seq OWNER TO postgres;

--
-- Name: subdocument_idsubdocument_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.subdocument_idsubdocument_seq OWNED BY public.subdocument.idsubdocument;


--
-- Name: topic; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.topic (
    idtopic integer NOT NULL,
    code character varying(255) NOT NULL,
    createdat timestamp without time zone NOT NULL,
    updatedat timestamp without time zone,
    enabled boolean NOT NULL
);


ALTER TABLE public.topic OWNER TO postgres;

--
-- Name: topic_idtopic_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.topic_idtopic_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.topic_idtopic_seq OWNER TO postgres;

--
-- Name: topic_idtopic_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.topic_idtopic_seq OWNED BY public.topic.idtopic;


--
-- Name: topictranslation; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.topictranslation (
    idtopic integer NOT NULL,
    idlanguage integer NOT NULL,
    name character varying(255),
    description text
);


ALTER TABLE public.topictranslation OWNER TO postgres;

--
-- Name: book idbook; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.book ALTER COLUMN idbook SET DEFAULT nextval('public.book_idbook_seq'::regclass);


--
-- Name: chunk idchunk; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chunk ALTER COLUMN idchunk SET DEFAULT nextval('public.chunk_idchunk_seq'::regclass);


--
-- Name: competence idcompetence; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.competence ALTER COLUMN idcompetence SET DEFAULT nextval('public.competence_idcompetence_seq'::regclass);


--
-- Name: competencelevel idcompetencelevel; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.competencelevel ALTER COLUMN idcompetencelevel SET DEFAULT nextval('public.competencelevel_idcompetencelevel_seq'::regclass);


--
-- Name: concept idconcept; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.concept ALTER COLUMN idconcept SET DEFAULT nextval('public.concept_idconcept_seq'::regclass);


--
-- Name: language idlanguage; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.language ALTER COLUMN idlanguage SET DEFAULT nextval('public.language_idlanguage_seq'::regclass);


--
-- Name: learningstep idstep; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.learningstep ALTER COLUMN idstep SET DEFAULT nextval('public.learningstep_idstep_seq'::regclass);


--
-- Name: learningunit idlearningunit; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.learningunit ALTER COLUMN idlearningunit SET DEFAULT nextval('public.learningunit_idlearningunit_seq'::regclass);


--
-- Name: subdocument idsubdocument; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subdocument ALTER COLUMN idsubdocument SET DEFAULT nextval('public.subdocument_idsubdocument_seq'::regclass);


--
-- Name: topic idtopic; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.topic ALTER COLUMN idtopic SET DEFAULT nextval('public.topic_idtopic_seq'::regclass);


--
-- Name: book book_code_unique; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.book
    ADD CONSTRAINT book_code_unique UNIQUE (code);


--
-- Name: book book_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.book
    ADD CONSTRAINT book_pkey PRIMARY KEY (idbook);


--
-- Name: chunk chunk_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chunk
    ADD CONSTRAINT chunk_pkey PRIMARY KEY (idchunk);


--
-- Name: language code_unique; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.language
    ADD CONSTRAINT code_unique UNIQUE (code);


--
-- Name: competence competence_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.competence
    ADD CONSTRAINT competence_pkey PRIMARY KEY (idcompetence);


--
-- Name: competenceconcept competenceconcept_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.competenceconcept
    ADD CONSTRAINT competenceconcept_pkey PRIMARY KEY (idcompetence, idconcept);


--
-- Name: competencelevel competencelevel_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.competencelevel
    ADD CONSTRAINT competencelevel_pkey PRIMARY KEY (idcompetencelevel);


--
-- Name: competenceleveltranslation competenceleveltranslation_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.competenceleveltranslation
    ADD CONSTRAINT competenceleveltranslation_pkey PRIMARY KEY (idcompetencelevel, idlanguage);


--
-- Name: competencetranslation competencetranslation_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.competencetranslation
    ADD CONSTRAINT competencetranslation_pkey PRIMARY KEY (idcompetence, idlanguage);


--
-- Name: concept concept_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.concept
    ADD CONSTRAINT concept_pkey PRIMARY KEY (idconcept);


--
-- Name: concepttranslation concepttranslation_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.concepttranslation
    ADD CONSTRAINT concepttranslation_pkey PRIMARY KEY (idconcept, idlanguage);


--
-- Name: language language_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.language
    ADD CONSTRAINT language_pkey PRIMARY KEY (idlanguage);


--
-- Name: learningstep learningstep_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.learningstep
    ADD CONSTRAINT learningstep_pkey PRIMARY KEY (idstep);


--
-- Name: learningsteptranslation learningsteptranslation_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.learningsteptranslation
    ADD CONSTRAINT learningsteptranslation_pkey PRIMARY KEY (idstep, idlanguage);


--
-- Name: learningunit learningunit_code_unique; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.learningunit
    ADD CONSTRAINT learningunit_code_unique UNIQUE (code);


--
-- Name: learningunit learningunit_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.learningunit
    ADD CONSTRAINT learningunit_pkey PRIMARY KEY (idlearningunit);


--
-- Name: learningunittranslation learningunittranslation_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.learningunittranslation
    ADD CONSTRAINT learningunittranslation_pkey PRIMARY KEY (idlearningunit, idlanguage);


--
-- Name: subdocument subdocument_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subdocument
    ADD CONSTRAINT subdocument_pkey PRIMARY KEY (idsubdocument);


--
-- Name: topic topic_code_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.topic
    ADD CONSTRAINT topic_code_key UNIQUE (code);


--
-- Name: topic topic_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.topic
    ADD CONSTRAINT topic_pkey PRIMARY KEY (idtopic);


--
-- Name: topictranslation topictranslation_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.topictranslation
    ADD CONSTRAINT topictranslation_pkey PRIMARY KEY (idtopic, idlanguage);


--
-- Name: chunklangchainvectorindex; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX chunklangchainvectorindex ON public.chunk USING hnsw (embedding public.halfvec_cosine_ops) WITH (m='16', ef_construction='64');


--
-- Name: fki_chunk_idcompetence_fkey; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX fki_chunk_idcompetence_fkey ON public.chunk USING btree (idcompetence);


--
-- Name: fki_chunk_idtopic_fkey; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX fki_chunk_idtopic_fkey ON public.chunk USING btree (idtopic);


--
-- Name: book book_idlanguage_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.book
    ADD CONSTRAINT book_idlanguage_fkey FOREIGN KEY (idlanguage) REFERENCES public.language(idlanguage);


--
-- Name: chunk chunk_idbook_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chunk
    ADD CONSTRAINT chunk_idbook_fkey FOREIGN KEY (idbook) REFERENCES public.book(idbook);


--
-- Name: chunk chunk_idcompetence_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chunk
    ADD CONSTRAINT chunk_idcompetence_fkey FOREIGN KEY (idcompetence) REFERENCES public.competence(idcompetence);


--
-- Name: chunk chunk_idlanguage_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chunk
    ADD CONSTRAINT chunk_idlanguage_fkey FOREIGN KEY (idlanguage) REFERENCES public.language(idlanguage);


--
-- Name: chunk chunk_idsubdocument_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chunk
    ADD CONSTRAINT chunk_idsubdocument_fkey FOREIGN KEY (idsubdocument) REFERENCES public.subdocument(idsubdocument) NOT VALID;


--
-- Name: chunk chunk_idtopic_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chunk
    ADD CONSTRAINT chunk_idtopic_fkey FOREIGN KEY (idtopic) REFERENCES public.topic(idtopic);


--
-- Name: competenceconcept competenceconcept_idcompetence_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.competenceconcept
    ADD CONSTRAINT competenceconcept_idcompetence_fkey FOREIGN KEY (idcompetence) REFERENCES public.competence(idcompetence);


--
-- Name: competenceconcept competenceconcept_idconcept_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.competenceconcept
    ADD CONSTRAINT competenceconcept_idconcept_fkey FOREIGN KEY (idconcept) REFERENCES public.concept(idconcept);


--
-- Name: competenceleveltranslation competenceleveltranslation_idcompetencelevel_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.competenceleveltranslation
    ADD CONSTRAINT competenceleveltranslation_idcompetencelevel_fkey FOREIGN KEY (idcompetencelevel) REFERENCES public.competencelevel(idcompetencelevel);


--
-- Name: competenceleveltranslation competenceleveltranslation_idlanguage_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.competenceleveltranslation
    ADD CONSTRAINT competenceleveltranslation_idlanguage_fkey FOREIGN KEY (idlanguage) REFERENCES public.language(idlanguage);


--
-- Name: competencetranslation competencetranslation_idcompetence_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.competencetranslation
    ADD CONSTRAINT competencetranslation_idcompetence_fkey FOREIGN KEY (idcompetence) REFERENCES public.competence(idcompetence);


--
-- Name: competencetranslation competencetranslation_idlanguage_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.competencetranslation
    ADD CONSTRAINT competencetranslation_idlanguage_fkey FOREIGN KEY (idlanguage) REFERENCES public.language(idlanguage);


--
-- Name: concepttranslation concepttranslation_idconcept_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.concepttranslation
    ADD CONSTRAINT concepttranslation_idconcept_fkey FOREIGN KEY (idconcept) REFERENCES public.concept(idconcept);


--
-- Name: concepttranslation concepttranslation_idlanguage_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.concepttranslation
    ADD CONSTRAINT concepttranslation_idlanguage_fkey FOREIGN KEY (idlanguage) REFERENCES public.language(idlanguage);


--
-- Name: learningsteptranslation learningsteptranslation_idlanguage_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.learningsteptranslation
    ADD CONSTRAINT learningsteptranslation_idlanguage_fkey FOREIGN KEY (idlanguage) REFERENCES public.language(idlanguage);


--
-- Name: learningsteptranslation learningsteptranslation_idstep_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.learningsteptranslation
    ADD CONSTRAINT learningsteptranslation_idstep_fkey FOREIGN KEY (idstep) REFERENCES public.learningstep(idstep);


--
-- Name: learningunit learningunit_idcompetencelevel_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.learningunit
    ADD CONSTRAINT learningunit_idcompetencelevel_fkey FOREIGN KEY (idcompetencelevel) REFERENCES public.competencelevel(idcompetencelevel);


--
-- Name: learningunit learningunit_idconcept_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.learningunit
    ADD CONSTRAINT learningunit_idconcept_fkey FOREIGN KEY (idconcept) REFERENCES public.concept(idconcept);


--
-- Name: learningunit learningunit_idstep_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.learningunit
    ADD CONSTRAINT learningunit_idstep_fkey FOREIGN KEY (idstep) REFERENCES public.learningstep(idstep);


--
-- Name: learningunittranslation learningunittranslation_idlanguage_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.learningunittranslation
    ADD CONSTRAINT learningunittranslation_idlanguage_fkey FOREIGN KEY (idlanguage) REFERENCES public.language(idlanguage);


--
-- Name: learningunittranslation learningunittranslation_idlearningunit_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.learningunittranslation
    ADD CONSTRAINT learningunittranslation_idlearningunit_fkey FOREIGN KEY (idlearningunit) REFERENCES public.learningunit(idlearningunit);


--
-- Name: subdocument subdocument_idbook_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subdocument
    ADD CONSTRAINT subdocument_idbook_fkey FOREIGN KEY (idbook) REFERENCES public.book(idbook);


--
-- Name: subdocument subdocument_idcompetence_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subdocument
    ADD CONSTRAINT subdocument_idcompetence_fkey FOREIGN KEY (idcompetence) REFERENCES public.competence(idcompetence);


--
-- Name: subdocument subdocument_idlanguage_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subdocument
    ADD CONSTRAINT subdocument_idlanguage_fkey FOREIGN KEY (idlanguage) REFERENCES public.language(idlanguage);


--
-- Name: subdocument subdocument_idtopic_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subdocument
    ADD CONSTRAINT subdocument_idtopic_fkey FOREIGN KEY (idtopic) REFERENCES public.topic(idtopic) NOT VALID;


--
-- Name: topictranslation topictranslation_idlanguage_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.topictranslation
    ADD CONSTRAINT topictranslation_idlanguage_fkey FOREIGN KEY (idlanguage) REFERENCES public.language(idlanguage);


--
-- Name: topictranslation topictranslation_idtopic_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.topictranslation
    ADD CONSTRAINT topictranslation_idtopic_fkey FOREIGN KEY (idtopic) REFERENCES public.topic(idtopic);


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE USAGE ON SCHEMA public FROM PUBLIC;


--
-- PostgreSQL database dump complete
--

