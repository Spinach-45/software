-- 不刪除或改寫任何既有報名；即使舊資料已重複，仍可安裝保護。
CREATE INDEX IF NOT EXISTS registrations_identity
ON registrations(event_id, trim(name), trim(phone));

CREATE TRIGGER IF NOT EXISTS registrations_no_duplicate_insert
BEFORE INSERT ON registrations
WHEN EXISTS (
  SELECT 1 FROM registrations
  WHERE event_id = NEW.event_id
    AND trim(name) = trim(NEW.name) AND trim(phone) = trim(NEW.phone)
)
BEGIN
  SELECT RAISE(ABORT, 'duplicate registration');
END;

CREATE TRIGGER IF NOT EXISTS registrations_no_duplicate_update
BEFORE UPDATE OF event_id, name, phone ON registrations
WHEN EXISTS (
  SELECT 1 FROM registrations
  WHERE event_id = NEW.event_id AND id <> OLD.id
    AND trim(name) = trim(NEW.name) AND trim(phone) = trim(NEW.phone)
)
BEGIN
  SELECT RAISE(ABORT, 'duplicate registration');
END;
