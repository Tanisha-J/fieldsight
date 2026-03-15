-- FieldSight Database Schema
-- Run this file in MySQL Workbench to set up the database

CREATE DATABASE IF NOT EXISTS fieldsight;
USE fieldsight;

-- -----------------------------------------------
-- Table 1: Farmers (AUTH)
-- -----------------------------------------------
CREATE TABLE Farmers (
    farmer_id   INT AUTO_INCREMENT PRIMARY KEY,
    first_name  VARCHAR(50)  NOT NULL,
    last_name   VARCHAR(50)  NOT NULL,
    username    VARCHAR(20)  UNIQUE NOT NULL,
    password_hash VARCHAR(20) NOT NULL,
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login  TIMESTAMP    NOT NULL,
    farm_name   VARCHAR(50)  NOT NULL
);

-- -----------------------------------------------
-- Table 2: Rover_Session
-- -----------------------------------------------
CREATE TABLE Rover_Session (
    session_id  INT AUTO_INCREMENT PRIMARY KEY,
    farmer_id   INT         NOT NULL,
    is_active   BOOLEAN     NOT NULL DEFAULT TRUE,
    start_time  TIMESTAMP   NULL,
    end_time    TIMESTAMP   NULL,
    status      ENUM('RUNNING', 'COMPLETED', 'IDLE') NOT NULL DEFAULT 'IDLE',

    CONSTRAINT fk_rover_farmer
        FOREIGN KEY (farmer_id) REFERENCES Farmers(farmer_id)
);

-- -----------------------------------------------
-- Table 3: Scans
-- -----------------------------------------------
CREATE TABLE Scans (
    scan_id        INT AUTO_INCREMENT PRIMARY KEY,
    session_id     INT          NOT NULL,
    farmer_id      INT          NOT NULL,
    disease_status ENUM('DISEASED', 'HEALTHY', 'NO PLANT') NOT NULL,
    image_url      VARCHAR(225) NOT NULL,
    image_key      VARCHAR(225) NOT NULL,
    severity       ENUM('YELLOW', 'RED', 'ORANGE') NOT NULL,
    gemini_status  VARCHAR(10)  NOT NULL,
    scanned_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    gps_lat        DOUBLE       NOT NULL,
    gps_lng        DOUBLE       NOT NULL,

    CONSTRAINT fk_scans_session
        FOREIGN KEY (session_id) REFERENCES Rover_Session(session_id),
    CONSTRAINT fk_scans_farmer
        FOREIGN KEY (farmer_id) REFERENCES Farmers(farmer_id)
);
