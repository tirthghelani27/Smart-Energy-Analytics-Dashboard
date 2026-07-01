-- ============================================================
-- Smart Energy Analytics Platform — Database Schema
-- MySQL 8.0+ compatible
--
-- Matches SQLAlchemy models in src/models/*.py exactly.
-- Run this AFTER creating the database (see instructions
-- at the end of the implementation summary).
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================
-- 1. users
-- ============================================================
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
    `id`          INT AUTO_INCREMENT PRIMARY KEY,
    `username`    VARCHAR(80)  NOT NULL,
    `email`       VARCHAR(120) NOT NULL,
    `password`    VARCHAR(255) NOT NULL,
    `first_name`  VARCHAR(50)  DEFAULT NULL,
    `last_name`   VARCHAR(50)  DEFAULT NULL,
    `role`        VARCHAR(20)  NOT NULL DEFAULT 'user',
    `is_active`   TINYINT(1)   NOT NULL DEFAULT 1,
    `last_login`  DATETIME     DEFAULT NULL,
    `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                               ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY `uq_users_username` (`username`),
    UNIQUE KEY `uq_users_email` (`email`),
    KEY `ix_users_username` (`username`),
    KEY `ix_users_email` (`email`),
    KEY `ix_users_role` (`role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 2. electricity_usage
-- ============================================================
DROP TABLE IF EXISTS `electricity_usage`;
CREATE TABLE `electricity_usage` (
    `id`              INT AUTO_INCREMENT PRIMARY KEY,
    `user_id`         INT NOT NULL,
    `date`            DATE NOT NULL,
    `units_consumed`  FLOAT NOT NULL,
    `cost`            FLOAT DEFAULT NULL,
    `tariff_rate`     FLOAT DEFAULT NULL,
    `source`          VARCHAR(50) NOT NULL DEFAULT 'manual',
    `notes`           TEXT DEFAULT NULL,
    `created_at`      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY `uq_user_date` (`user_id`, `date`),
    KEY `ix_electricity_usage_user_id` (`user_id`),
    KEY `ix_electricity_usage_date` (`date`),

    CONSTRAINT `fk_usage_user`
        FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 3. appliances
-- ============================================================
DROP TABLE IF EXISTS `appliances`;
CREATE TABLE `appliances` (
    `id`               INT AUTO_INCREMENT PRIMARY KEY,
    `user_id`          INT NOT NULL,
    `name`             VARCHAR(100) NOT NULL,
    `category`         VARCHAR(50)  DEFAULT NULL,
    `power_rating_w`   FLOAT NOT NULL,
    `daily_usage_hrs`  FLOAT NOT NULL,
    `monthly_kwh`      FLOAT DEFAULT NULL,
    `monthly_cost`     FLOAT DEFAULT NULL,
    `is_active`        TINYINT(1) NOT NULL DEFAULT 1,
    `created_at`       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    KEY `ix_appliances_user_id` (`user_id`),
    KEY `ix_appliances_category` (`category`),

    CONSTRAINT `fk_appliance_user`
        FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 4. predictions
-- ============================================================
DROP TABLE IF EXISTS `predictions`;
CREATE TABLE `predictions` (
    `id`               INT AUTO_INCREMENT PRIMARY KEY,
    `user_id`          INT NOT NULL,
    `prediction_date`  DATE NOT NULL,
    `period`           VARCHAR(20) NOT NULL,
    `predicted_units`  FLOAT NOT NULL,
    `predicted_cost`   FLOAT DEFAULT NULL,
    `model_used`       VARCHAR(50) DEFAULT NULL,
    `mae`              FLOAT DEFAULT NULL,
    `rmse`             FLOAT DEFAULT NULL,
    `r2_score`         FLOAT DEFAULT NULL,
    `created_at`       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    KEY `ix_predictions_user_id` (`user_id`),
    KEY `ix_predictions_period` (`period`),
    KEY `ix_predictions_model_used` (`model_used`),

    CONSTRAINT `fk_prediction_user`
        FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 5. alerts
-- ============================================================
DROP TABLE IF EXISTS `alerts`;
CREATE TABLE `alerts` (
    `id`            INT AUTO_INCREMENT PRIMARY KEY,
    `user_id`       INT NOT NULL,
    `alert_type`    VARCHAR(50) NOT NULL,
    `severity`      VARCHAR(20) NOT NULL,
    `message`       TEXT NOT NULL,
    `is_read`       TINYINT(1) NOT NULL DEFAULT 0,
    `triggered_at`  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    KEY `ix_alerts_user_id` (`user_id`),
    KEY `ix_alerts_severity` (`severity`),
    KEY `ix_alerts_is_read` (`is_read`),

    CONSTRAINT `fk_alert_user`
        FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 6. recommendations
-- ============================================================
DROP TABLE IF EXISTS `recommendations`;
CREATE TABLE `recommendations` (
    `id`                     INT AUTO_INCREMENT PRIMARY KEY,
    `user_id`                INT NOT NULL,
    `category`               VARCHAR(50)  NOT NULL,
    `title`                  VARCHAR(200) NOT NULL,
    `description`            TEXT NOT NULL,
    `potential_saving_kwh`   FLOAT DEFAULT NULL,
    `potential_saving_cost`  FLOAT DEFAULT NULL,
    `priority`               VARCHAR(20) NOT NULL DEFAULT 'medium',
    `is_applied`             TINYINT(1) NOT NULL DEFAULT 0,
    `created_at`             DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    KEY `ix_recommendations_user_id` (`user_id`),
    KEY `ix_recommendations_category` (`category`),
    KEY `ix_recommendations_priority` (`priority`),
    KEY `ix_recommendations_is_applied` (`is_applied`),

    CONSTRAINT `fk_recommendation_user`
        FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 7. carbon_footprint
--    (matches SQLAlchemy model __tablename__ = "carbon_footprint")
-- ============================================================
DROP TABLE IF EXISTS `carbon_footprint`;
CREATE TABLE `carbon_footprint` (
    `id`                     INT AUTO_INCREMENT PRIMARY KEY,
    `user_id`                INT NOT NULL,
    `month`                  INT NOT NULL,
    `year`                   INT NOT NULL,
    `co2_generated`          FLOAT NOT NULL,
    `co2_saved`              FLOAT DEFAULT 0.0,
    `trees_equivalent`       FLOAT DEFAULT NULL,
    `sustainability_score`   FLOAT DEFAULT NULL,
    `created_at`             DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY `uq_user_month_year` (`user_id`, `month`, `year`),
    KEY `ix_carbon_footprint_user_id` (`user_id`),
    KEY `ix_carbon_footprint_year_month` (`year`, `month`),

    CONSTRAINT `fk_carbon_user`
        FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 8. reports
-- ============================================================
DROP TABLE IF EXISTS `reports`;
CREATE TABLE `reports` (
    `id`            INT AUTO_INCREMENT PRIMARY KEY,
    `user_id`       INT NOT NULL,
    `title`         VARCHAR(200) NOT NULL,
    `report_type`   VARCHAR(50)  NOT NULL,
    `file_path`     VARCHAR(500) DEFAULT NULL,
    `generated_at`  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    KEY `ix_reports_user_id` (`user_id`),
    KEY `ix_reports_report_type` (`report_type`),
    KEY `ix_reports_generated_at` (`generated_at`),

    CONSTRAINT `fk_report_user`
        FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


SET FOREIGN_KEY_CHECKS = 1;
