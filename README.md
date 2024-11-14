 Quick Start Guide

## Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   ```

2. **Prepare Database and Log Files**
   ```bash
   touch audit.log phonebook.db test.db
   chmod 777 audit.log phonebook.db test.db
   ```

3. **Edit `docker-compose.yml`**
   - Update paths in `docker-compose.yml` to reflect your local storage for data persistence. Replace:
     ```yaml
     - "/home/thetemplemann/UT Arlington Local/Secure Programming/test/phonebook.db:/app/phonebook.db"
     - "/home/thetemplemann/UT Arlington Local/Secure Programming/test/audit.log:/app/audit.log"
     - "/home/thetemplemann/UT Arlington Local/Secure Programming/test/test.db:/app/test.db"
     ```
   - Adjust paths as necessary for your setup. Remember to replace paths in test service if running tests 

4. **Build and Run Docker**
   ```bash
   docker compose build && docker compose up
   ```
   *Note:* To skip tests, comment out  `test service` in `docker-compose.yml`.

## Testing Instructions

- By default, tests will run automatically. For detailed testing instructions, refer to the full documentation.
- **Testing with Postman**:
   - First, `/register` a user with either a `READ` or `READ_WRITE` role.
   - Use the provided auth token in Postman’s Auth settings to perform operations.

5. **Reset the Database if Needed**
   - To clear persisted data in `phonebook.db` or `test.db`, use:
     ```bash
     sqlite3 phonebook.db < deltables.sql
     ```
