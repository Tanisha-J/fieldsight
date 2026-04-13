--v2

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
    stopped_at TIMESTAMP NOT NULL,
    status ENUM('Running', 'Stopped', 'Processing', 'Completed') NOT NULL DEFAULT 'IDLE',
    last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    active_command ENUM('idle', 'stop', 'start') NOT NULL DEFAULT 'IDLE',
    
    -- This creates the "link" to the Farmers table
    FOREIGN KEY (farmer_id) REFERENCES Farmers(farmer_id)
);

CREATE TABLE IF NOT EXISTS Scans (
    scan_id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    farmer_id INT NOT NULL,
    disease_status ENUM('DISEASED', 'HEALTHY', 'NO PLANT') NOT NULL,
    image_url VARCHAR(225) NOT NULL,
    image_key VARCHAR(225) NOT NULL,
    severity ENUM('YELLOW', 'RED', 'ORANGE') NOT NULL,
    gemini_status VARCHAR(10),
    scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    gps_lat DOUBLE NOT NULL,
    gps_lng DOUBLE NOT NULL,

    -- Establishing the relationships
    FOREIGN KEY (session_id) REFERENCES Rover_Sessions(session_id),
    FOREIGN KEY (farmer_id) REFERENCES Farmers(farmer_id)
);