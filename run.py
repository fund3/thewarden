# When creating packages, the import app below gets from
# __init__.py file`
from flask_migrate import Migrate
from thewarden import create_app, db
from thewarden.models import listofcrypto, User, Trades, AccountInfo, Contact

# CLS + Welcome
print("\033[1;32;40m")
for _ in range(50):
    print("")
print(f"""
\033[1;32;40m
-----------------------------------------------------------------
      _   _           __        ___    ____     _
     | |_| |__   ___  \ \      / / \  |  _ \ __| | ___ _ __
     | __| '_ \ / _ \  \ \ /\ / / _ \ | |_) / _` |/ _ \ '_  |
     | |_| | | |  __/   \ V  V / ___ \|  _ < (_| |  __/ | | |
      \__|_| |_|\___|    \_/\_/_/   \_\_| \_\__,_|\___|_| |_|

-----------------------------------------------------------------
               \033[1;37;40m
       Privacy Focused Portfolio & Bitcoin Address Tracker
\033[1;32;40m-----------------------------------------------------------------
\033[1;37;40m
   Application loaded...
   You can access it at your browser
   Just go to:
   \033[1;32;40mhttp://127.0.0.1:5000/
   \033[1;37;40mTo change the ip above:
   \033[1;32;40mpython run.py --host [host_ip]
   \033[1;37;40mTO EXIT HIT CTRL+C a couple of times
   You can minimize this window now...

\033[1;32;40m-----------------------------------------------------------------
\033[1;31;40m                  Always go for the red pill
\033[1;32;40m-----------------------------------------------------------------
\033[1;37;40m
""")

app = create_app()
app.app_context().push()
migrate = Migrate(app, db, render_as_batch=True)


@app.shell_context_processor
def make_shell_context():
    return dict(
        db=db,
        User=User,
        listofcrypto=listofcrypto,
        Trades=Trades,
        AccountInfo=AccountInfo,
        Contact=Contact,
    )


if __name__ == "__main__":
    app.run(debug=True, threaded=True)
