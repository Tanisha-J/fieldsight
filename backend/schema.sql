-- v2

CREATE TABLE IF NOT EXISTS Farmers (
    farmer_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    username VARCHAR(20) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL, -- Increased size for security hashes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_login TIMESTAMP NULL,
    farm_name VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS Rover_Sessions (
    session_id INT AUTO_INCREMENT PRIMARY KEY,
    farmer_id INT NOT NULL,
    session_date DATE NOT NULL,
    started_at TIMESTAMP NULL,
    stopped_at TIMESTAMP NULL,
    status ENUM('Running', 'Stopped', 'Processing', 'Completed') NOT NULL DEFAULT 'Stopped',
    last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    active_command ENUM('idle', 'stop', 'start') NOT NULL DEFAULT 'idle',
    
    -- This creates the "link" to the Farmers table
    FOREIGN KEY (farmer_id) REFERENCES Farmers(farmer_id)
);

CREATE TABLE IF NOT EXISTS Scans (
    scan_id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NULL,
    farmer_id INT NOT NULL,
    disease_status ENUM('DISEASED', 'HEALTHY', 'NO PLANT') NOT NULL,
    image_url VARCHAR(255) NOT NULL,
    image_key VARCHAR(255) NOT NULL,
    severity ENUM('YELLOW', 'RED', 'ORANGE') NOT NULL,
    gemini_status VARCHAR(20),
    scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    gps_lat DOUBLE NOT NULL,
    gps_lng DOUBLE NOT NULL,

    -- Establishing the relationships
    FOREIGN KEY (session_id) REFERENCES Rover_Sessions(session_id),
    FOREIGN KEY (farmer_id) REFERENCES Farmers(farmer_id)
);

CREATE TABLE IF NOT EXISTS Telemetry (
    telemetry_id BIGINT AUTO_INCREMENT PRIMARY KEY, -- Unique ID for each telemetry row
    session_id INT NOT NULL,    -- points towards all telemetry rows in that session
    rover_id INT NOT NULL,
    battery DOUBLE NOT NULL,    
    gps_lat DOUBLE NOT NULL,
    gps_lng DOUBLE NOT NULL,
    heading DOUBLE NULL,    -- orientation angle
    captured_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,   -- timestamp of reading

    -- Makes lookups faster when searching by session and time 
    INDEX idx_telemetry_session_time (session_id, captured_at),

    -- speeds up look up when searching by rover and time 
    INDEX idx_telemetry_rover_time (rover_id, captured_at),

    -- Ensures telemetry rows point towards an actual session ID
    FOREIGN KEY (session_id) REFERENCES Rover_Sessions(session_id)
);