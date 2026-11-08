
/*******************************************************************************
   scout_assessment Database - Version 1.0.0
   Script: SCOUT_ASSESSMENT_MYSQL.sql
   Description: Creates and seeds database for scheduling and tracking
   scout program assessments.
   DB Server: MySQL
   Authors: Brad Spoerri, Sam Whitaker, Chaitanya Patil
   License: #TODO
********************************************************************************/


/*******************************************************************************
   Drop database if it exists
********************************************************************************/
DROP DATABASE IF EXISTS scout_assessment;

/*******************************************************************************
   Create database
********************************************************************************/
CREATE DATABASE scout_assessment;

/*******************************************************************************
   Activate database
********************************************************************************/
USE scout_assessment;

/*******************************************************************************
   Create Tables
********************************************************************************/

CREATE TABLE council (
	council_num		INT				PRIMARY KEY,
	council_name	VARCHAR(60)		NOT NULL
);


CREATE TABLE volunteer (
	volunteer_id	INT				PRIMARY KEY,
	council_num		INT				NOT NULL,
	first_name		VARCHAR(45)		NOT NULL,
	pref_name		VARCHAR(30),
	last_name		VARCHAR(45)		NOT NULL,
	email			VARCHAR(60)		NOT NULL UNIQUE,
	phone			VARCHAR(15)		NOT NULL,
	tenure			VARCHAR(15)		NOT NULL,
	
	FOREIGN KEY (council_num) REFERENCES council (council_num),
	
	CONSTRAINT check_tenure 
		CHECK (tenure IN ('first-time', 'experienced'))
);

CREATE TABLE camp (
	camp_id			INT				AUTO_INCREMENT	PRIMARY KEY,
	camp_name		VARCHAR(60)		NOT NULL UNIQUE,
	council_num		INT				NOT NULL,
	director_name	VARCHAR(60)		NOT NULL,
	director_email	VARCHAR(60)		NOT NULL,
	street			VARCHAR(60)		NOT NULL,
	city			VARCHAR(45)		NOT NULL,
	state			VARCHAR(30),
	country			VARCHAR(45)		NOT NULL,
	ito_code		VARCHAR(15)		NOT NULL,
	
	FOREIGN KEY (council_num) REFERENCES council (council_num)
);

CREATE TABLE program (
	program_id		INT				AUTO_INCREMENT	PRIMARY KEY,
	program_name	VARCHAR(45)		NOT NULL,
	max_score		INT				NOT NULL
);

CREATE TABLE assessment (
	assessment_id		INT			AUTO_INCREMENT	PRIMARY KEY,
	camp_id 			INT			NOT NULL,
	program_id			INT			NOT NULL,
	assessment_date		DATE		NOT NULL,
	required_assessors	INT			NOT NULL,
	completed_ind		BOOLEAN		DEFAULT FALSE,
	
	FOREIGN KEY (camp_id) REFERENCES camp (camp_id),
	FOREIGN KEY (program_id) REFERENCES program (program_id)
);


#TODO

/*
 We must strategize how to insert indicator fields.

 */

CREATE TABLE assessment_assignment (
    assignment_idx   INT      AUTO_INCREMENT PRIMARY KEY,
    assessment_id    INT      NOT NULL,
    volunteer_id     INT      NOT NULL,
    lead_ind         BOOLEAN  NOT NULL DEFAULT FALSE,
    alternate_ind    BOOLEAN  NOT NULL DEFAULT FALSE,
    first_time_ind   BOOLEAN  NOT NULL DEFAULT FALSE,
    
	FOREIGN KEY (assessment_id) REFERENCES assessment (assessment_id),
	FOREIGN KEY (volunteer_id) REFERENCES volunteer (volunteer_id),

    CONSTRAINT lead_eligible
        CHECK (NOT (lead_ind AND (alternate_ind OR first_time_ind))),
    
    CONSTRAINT unique_instance
        UNIQUE (assessment_id, volunteer_id)
);





