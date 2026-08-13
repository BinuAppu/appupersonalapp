from flask import Flask, render_template, request, jsonify, redirect, url_for
import csv
import io
import os
import re
import shutil
import time
import requests
from datetime import datetime, timedelta
from data_manager import DataManager

app = Flask(__name__)
data_manager = DataManager()

@app.template_filter('short_date')
def short_date_filter(value):
    if not value: return ""
    try:
        if isinstance(value, str):
            dt = datetime.fromisoformat(value)
        else:
            dt = value
        return dt.strftime('%m/%d')
    except:
        return value

@app.template_filter('days_since')
def days_since_filter(value):
    if not value: return 9999
    try:
        dt = datetime.fromisoformat(value) if isinstance(value, str) else value
        return (datetime.now() - dt).days
    except:
        return 9999

@app.template_filter('days_until')
def days_until_filter(date_str):
    if not date_str: return 999
    try:
        if isinstance(date_str, str):
            # Try ISO format first
            try:
                rem_date = datetime.fromisoformat(date_str).date()
            except:
                # Try YYYY-MM-DD format
                rem_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        else:
            rem_date = date_str
        today = datetime.now().date()
        delta = (rem_date - today).days
        return delta
    except:
        return 999

def _reminder_alert_color(reminder, colors):
    days_until = days_until_filter(reminder.get("display_date") or reminder.get("date"))
    if days_until < 0:
        return colors.get("overdue", "#8B0000")
    if days_until <= 7:
        return colors.get("nearing_1_week", "#E53935")
    if days_until <= 14:
        return colors.get("nearing_2_weeks", "#F4C430")
    return ""

@app.context_processor
def inject_reminder_flash():
    settings = data_manager.get_settings()
    colors = settings.get("colors", {})
    reminders = data_manager.get_upcoming_reminders(weeks=12)
    flash_items = []

    for reminder in reminders[:5]:
        item = reminder.copy()
        item["alert_color"] = _reminder_alert_color(item, colors)
        item["days_until"] = days_until_filter(item.get("display_date") or item.get("date"))
        flash_items.append(item)

    urgent_count = len([item for item in reminders if _reminder_alert_color(item, colors)])
    bell_color = flash_items[0]["alert_color"] if flash_items and flash_items[0]["alert_color"] else colors.get("nearing_2_weeks", "#F4C430")

    return {
        "reminder_flash_items": flash_items,
        "reminder_flash_count": urgent_count or len(flash_items),
        "reminder_flash_color": bell_color
    }

AD_UAC_FLAGS = {
    "ACCOUNTDISABLE": 0x0002,
    "LOCKOUT": 0x0010,
    "PASSWD_NOTREQD": 0x0020,
    "PASSWD_CANT_CHANGE": 0x0040,
    "ENCRYPTED_TEXT_PWD_ALLOWED": 0x0080,
    "DONT_EXPIRE_PASSWORD": 0x10000,
    "SMARTCARD_REQUIRED": 0x40000,
    "TRUSTED_FOR_DELEGATION": 0x80000,
    "NOT_DELEGATED": 0x100000,
    "USE_DES_KEY_ONLY": 0x200000,
    "DONT_REQ_PREAUTH": 0x400000,
    "PASSWORD_EXPIRED": 0x800000,
    "TRUSTED_TO_AUTH_FOR_DELEGATION": 0x1000000,
}

AD_RISK_DEFINITIONS = {
    "disabled_users": {
        "title": "Disabled Users",
        "severity": "info",
        "description": "Accounts marked disabled in AD.",
    },
    "inactive_users": {
        "title": "Inactive Users",
        "severity": "high",
        "description": "Enabled accounts with no recent logon activity.",
    },
    "password_never_expires": {
        "title": "Password Never Expires",
        "severity": "high",
        "description": "Accounts where password expiry is bypassed.",
    },
    "password_not_required": {
        "title": "Password Not Required",
        "severity": "critical",
        "description": "Accounts that may be allowed to exist without a password.",
    },
    "cannot_change_password": {
        "title": "Cannot Change Password",
        "severity": "medium",
        "description": "Accounts flagged or exported as unable to change password.",
    },
    "asrep_roastable": {
        "title": "AS-REP Roastable",
        "severity": "critical",
        "description": "Kerberos pre-authentication is not required.",
    },
    "spn_kerberoast": {
        "title": "SPN / Kerberoast Exposure",
        "severity": "high",
        "description": "User accounts with SPNs can be targeted for Kerberoasting.",
    },
    "delegation_risk": {
        "title": "Delegation Risk",
        "severity": "critical",
        "description": "Accounts trusted for unconstrained or protocol-transition delegation.",
    },
    "weak_encryption": {
        "title": "Weak Kerberos Encryption",
        "severity": "high",
        "description": "DES/RC4-only or no AES-capable encryption indicators.",
    },
    "reversible_password": {
        "title": "Reversible Password Storage",
        "severity": "critical",
        "description": "Accounts allowing encrypted text passwords.",
    },
    "critical_system_object": {
        "title": "Critical System Object",
        "severity": "high",
        "description": "Accounts marked as critical AD system objects.",
    },
    "privileged_account": {
        "title": "Privileged Account",
        "severity": "high",
        "description": "AdminCount or privileged group membership was detected.",
    },
    "stale_password": {
        "title": "Stale Password",
        "severity": "medium",
        "description": "Password has not changed within the configured threshold.",
    },
    "password_expired": {
        "title": "Password Expired",
        "severity": "medium",
        "description": "Password is expired or must be changed.",
    },
    "smartcard_missing": {
        "title": "Privileged Without Smart Card",
        "severity": "medium",
        "description": "Privileged account without a smart-card-required indicator.",
    },
    "locked_out": {
        "title": "Locked Out",
        "severity": "low",
        "description": "Accounts currently marked as locked out.",
    },
}

AD_HEADER_ALIASES = {
    "name": ["name", "displayname", "cn", "samaccountname", "userprincipalname"],
    "sam": ["samaccountname", "samaccount", "accountname", "logonname"],
    "upn": ["userprincipalname", "upn"],
    "enabled": ["enabled", "isaccountenabled", "accountenabled"],
    "uac": ["useraccountcontrol", "uac", "useraccountcontrolvalue"],
    "password_never_expires": ["passwordneverexpires", "pwdneverexpires", "dontexpirepassword"],
    "password_not_required": ["passwordnotrequired", "passwdnotreqd"],
    "cannot_change_password": ["cannotchangepassword", "passwordcantchange", "passwd_cant_change"],
    "preauth_not_required": ["doesnotrequirepreauth", "donotrequirekerberospreauthentication", "dontreqpreauth", "preauthnotrequired"],
    "last_logon": ["lastlogontimestamp", "lastlogondate", "lastlogon", "lastlogontime", "lastlogonldap"],
    "pwd_last_set": ["pwdlastset", "passwordlastset", "pwdlastsetdate"],
    "spn": ["serviceprincipalname", "serviceprincipalnames", "spn"],
    "admin_count": ["admincount"],
    "member_of": ["memberof", "groups", "memberofgroups"],
    "delegation": ["trustedfordelegation", "trustedtoauthfordelegation", "accountnotdelegated"],
    "rbcd_delegation": ["principalsallowedtodelegatetoaccount", "msds-allowedtoactonbehalfofotheridentity", "msdsallowedtoactonbehalfofotheridentity"],
    "enc_types": ["msds-supportedencryptiontypes", "msdssupportedencryptiontypes", "supportedencryptiontypes"],
    "created": ["whencreated", "created", "creationdate"],
    "locked_out": ["lockedout", "islockedout"],
    "password_expired": ["passwordexpired", "pwdexpired"],
    "smartcard_required": ["smartcardlogonrequired", "smartcardrequired"],
    "reversible_password_setting": ["allowreversiblepasswordencryption", "reversiblepasswordencryptionenabled", "reversiblepassword"],
    "critical_system_object": ["iscriticalsystemobject", "criticalsystemobject"],
}

PRIVILEGED_GROUP_MARKERS = [
    "domain admins", "enterprise admins", "schema admins", "administrators",
    "account operators", "server operators", "backup operators", "dnsadmins",
    "group policy creator owners", "organization management",
]

def _normalize_header(value):
    return re.sub(r"[^a-z0-9]", "", (value or "").strip().lower())

def _first_value(row, header_map, logical_name):
    for alias in AD_HEADER_ALIASES.get(logical_name, []):
        key = header_map.get(_normalize_header(alias))
        if key is not None:
            value = row.get(key)
            if value is not None and str(value).strip() != "":
                return str(value).strip()
    return ""

def _parse_bool(value):
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"true", "$true", "yes", "y", "1", "enabled", "enable", "on"}:
        return True
    if text in {"false", "$false", "no", "n", "0", "disabled", "disable", "off"}:
        return False
    return None

def _parse_int(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        if text.lower().startswith("0x"):
            return int(text, 16)
        return int(float(text))
    except (TypeError, ValueError):
        return None

def _parse_multi_value(value):
    if value is None:
        return []
    text = str(value).strip()
    if not text:
        return []

    placeholder_values = {
        "microsoft.activedirectory.management.adpropertyvaluecollection",
        "system.string[]",
        "system.object[]",
        "default",
        "error",
        "none",
        "null",
        "n/a",
        "na",
        "-",
        "[]",
        "{}",
    }
    if text.strip().lower() in placeholder_values:
        return []

    text = text.strip("{}[]")
    parts = re.split(r"[\r\n;|]+|,\s+(?=[^/,\s]+/)", text)
    values = []
    for part in parts:
        clean = part.strip().strip('"').strip("'")
        if clean and clean.lower() not in placeholder_values:
            values.append(clean)
    return values

def _parse_spn_values(value):
    spn_pattern = re.compile(r"^[a-z][a-z0-9.+-]*/[^\s,;{}]+$", re.IGNORECASE)
    return [item for item in _parse_multi_value(value) if spn_pattern.match(item)]

def _parse_ad_datetime(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text or text in {"0", "9223372036854775807", "16010101000000.0Z"}:
        return None
    filetime = _parse_int(text)
    if filetime and filetime > 100000000000000000:
        try:
            return datetime(1601, 1, 1) + timedelta(microseconds=filetime / 10)
        except (OverflowError, ValueError):
            return None
    formats = [
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d",
        "%m/%d/%Y %H:%M:%S", "%m/%d/%Y", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y",
        "%Y%m%d%H%M%S.0Z", "%Y%m%d%H%M%SZ",
    ]
    clean_text = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(clean_text).replace(tzinfo=None)
    except ValueError:
        pass
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None

def _has_uac_flag(uac_value, flag_name):
    return uac_value is not None and bool(uac_value & AD_UAC_FLAGS[flag_name])

def _add_risk(account_risks, risk_counts, risk_key, evidence):
    account_risks.append({
        "key": risk_key,
        "title": AD_RISK_DEFINITIONS[risk_key]["title"],
        "severity": AD_RISK_DEFINITIONS[risk_key]["severity"],
        "evidence": evidence,
    })
    risk_counts[risk_key] = risk_counts.get(risk_key, 0) + 1

def _analyze_ad_rows(rows, headers, inactive_days=90, stale_password_days=180):
    header_map = {_normalize_header(header): header for header in headers}
    now = datetime.now()
    risk_counts = {key: 0 for key in AD_RISK_DEFINITIONS}
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    analyzed_accounts = []

    for index, row in enumerate(rows, start=1):
        uac = _parse_int(_first_value(row, header_map, "uac"))
        enabled_value = _parse_bool(_first_value(row, header_map, "enabled"))
        is_disabled = _has_uac_flag(uac, "ACCOUNTDISABLE") or enabled_value is False
        is_enabled = not is_disabled
        account_risks = []

        sam = _first_value(row, header_map, "sam")
        upn = _first_value(row, header_map, "upn")
        display_name = _first_value(row, header_map, "name") or sam or upn or f"Row {index}"
        member_of = _first_value(row, header_map, "member_of").lower()
        admin_count = _parse_int(_first_value(row, header_map, "admin_count"))
        is_privileged = admin_count == 1 or any(marker in member_of for marker in PRIVILEGED_GROUP_MARKERS)

        if is_disabled:
            _add_risk(account_risks, risk_counts, "disabled_users", "Disabled via Enabled=false or ACCOUNTDISABLE.")
        if _has_uac_flag(uac, "LOCKOUT") or _parse_bool(_first_value(row, header_map, "locked_out")) is True:
            _add_risk(account_risks, risk_counts, "locked_out", "LockedOut=true or LOCKOUT flag is set.")
        if _has_uac_flag(uac, "DONT_EXPIRE_PASSWORD") or _parse_bool(_first_value(row, header_map, "password_never_expires")) is True:
            _add_risk(account_risks, risk_counts, "password_never_expires", "DONT_EXPIRE_PASSWORD or PasswordNeverExpires is set.")
        if _has_uac_flag(uac, "PASSWD_NOTREQD") or _parse_bool(_first_value(row, header_map, "password_not_required")) is True:
            _add_risk(account_risks, risk_counts, "password_not_required", "PASSWD_NOTREQD or PasswordNotRequired is set.")
        if _has_uac_flag(uac, "PASSWD_CANT_CHANGE") or _parse_bool(_first_value(row, header_map, "cannot_change_password")) is True:
            _add_risk(account_risks, risk_counts, "cannot_change_password", "PASSWD_CANT_CHANGE or CannotChangePassword is set.")
        if _has_uac_flag(uac, "DONT_REQ_PREAUTH") or _parse_bool(_first_value(row, header_map, "preauth_not_required")) is True:
            _add_risk(account_risks, risk_counts, "asrep_roastable", "DONT_REQ_PREAUTH or pre-auth-not-required is set.")
        reversible_password_setting = _parse_bool(_first_value(row, header_map, "reversible_password_setting"))
        if _has_uac_flag(uac, "ENCRYPTED_TEXT_PWD_ALLOWED") or reversible_password_setting is True:
            _add_risk(account_risks, risk_counts, "reversible_password", "ENCRYPTED_TEXT_PWD_ALLOWED or AllowReversiblePasswordEncryption is set.")
        if _has_uac_flag(uac, "PASSWORD_EXPIRED") or _parse_bool(_first_value(row, header_map, "password_expired")) is True:
            _add_risk(account_risks, risk_counts, "password_expired", "PASSWORD_EXPIRED or PasswordExpired is set.")
        if _has_uac_flag(uac, "TRUSTED_FOR_DELEGATION") or _has_uac_flag(uac, "TRUSTED_TO_AUTH_FOR_DELEGATION"):
            _add_risk(account_risks, risk_counts, "delegation_risk", "Trusted delegation UAC flag is set.")
        rbcd_principals = _parse_multi_value(_first_value(row, header_map, "rbcd_delegation"))
        if rbcd_principals:
            _add_risk(account_risks, risk_counts, "delegation_risk", f"PrincipalsAllowedToDelegateToAccount contains {', '.join(rbcd_principals[:3])}.")

        spn_value = _first_value(row, header_map, "spn")
        spn_values = _parse_spn_values(spn_value)
        has_spn = bool(spn_values)
        if has_spn and is_enabled:
            _add_risk(account_risks, risk_counts, "spn_kerberoast", f"SPN present: {', '.join(spn_values[:3])}.")

        enc_raw = _first_value(row, header_map, "enc_types")
        enc_column_present = any(_normalize_header(alias) in header_map for alias in AD_HEADER_ALIASES["enc_types"])
        enc_types = _parse_int(enc_raw)
        has_aes = enc_types is not None and bool(enc_types & (0x08 | 0x10))
        rc4_only = enc_types in {0x04, 0x06}
        missing_enc_for_spn = has_spn and enc_column_present and not enc_raw
        if _has_uac_flag(uac, "USE_DES_KEY_ONLY") or rc4_only or missing_enc_for_spn or (has_spn and enc_types is not None and not has_aes):
            if _has_uac_flag(uac, "USE_DES_KEY_ONLY"):
                evidence = "USE_DES_KEY_ONLY is set."
            elif missing_enc_for_spn:
                evidence = "Service account has SPN but no msDS-SupportedEncryptionTypes value in the export."
            else:
                evidence = "msDS-SupportedEncryptionTypes does not include AES."
            _add_risk(account_risks, risk_counts, "weak_encryption", evidence)

        if is_privileged:
            _add_risk(account_risks, risk_counts, "privileged_account", "adminCount=1 or privileged group membership found.")
            smartcard = _parse_bool(_first_value(row, header_map, "smartcard_required"))
            if not _has_uac_flag(uac, "SMARTCARD_REQUIRED") and smartcard is not True:
                _add_risk(account_risks, risk_counts, "smartcard_missing", "Privileged account lacks a smart-card-required indicator.")

        if _parse_bool(_first_value(row, header_map, "critical_system_object")) is True:
            _add_risk(account_risks, risk_counts, "critical_system_object", "isCriticalSystemObject is true.")

        last_logon = _parse_ad_datetime(_first_value(row, header_map, "last_logon"))
        created = _parse_ad_datetime(_first_value(row, header_map, "created"))
        logon_reference = last_logon or created
        if is_enabled and logon_reference and (now - logon_reference).days >= inactive_days:
            _add_risk(account_risks, risk_counts, "inactive_users", f"No recent logon indicator for {(now - logon_reference).days} days.")

        pwd_last_set = _parse_ad_datetime(_first_value(row, header_map, "pwd_last_set"))
        if is_enabled and pwd_last_set and (now - pwd_last_set).days >= stale_password_days:
            _add_risk(account_risks, risk_counts, "stale_password", f"Password age is {(now - pwd_last_set).days} days.")
        elif is_enabled and _first_value(row, header_map, "pwd_last_set") == "0":
            _add_risk(account_risks, risk_counts, "password_expired", "pwdLastSet=0 indicates change password at next logon.")

        highest_severity = "none"
        if account_risks:
            severity_order = ["critical", "high", "medium", "low", "info"]
            highest_severity = min((risk["severity"] for risk in account_risks), key=severity_order.index)
            severity_counts[highest_severity] += 1

        analyzed_accounts.append({
            "row": index,
            "name": display_name,
            "sam": sam,
            "upn": upn,
            "enabled": is_enabled,
            "uac": uac,
            "spns": spn_values,
            "principals_allowed_to_delegate": rbcd_principals,
            "risk_count": len(account_risks),
            "highest_severity": highest_severity,
            "risks": account_risks,
        })

    risky_accounts = [account for account in analyzed_accounts if account["risk_count"] > 0]
    risky_accounts.sort(key=lambda item: (
        {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4, "none": 5}[item["highest_severity"]],
        -item["risk_count"],
        item["name"].lower()
    ))

    total_risk_instances = sum(risk_counts.values())
    return {
        "summary": {
            "total_accounts": len(rows),
            "risky_accounts": len(risky_accounts),
            "total_risk_instances": total_risk_instances,
            "critical_accounts": severity_counts["critical"],
            "high_accounts": severity_counts["high"],
            "medium_accounts": severity_counts["medium"],
            "low_accounts": severity_counts["low"],
            "info_accounts": severity_counts["info"],
            "inactive_days": inactive_days,
            "stale_password_days": stale_password_days,
        },
        "headers": headers,
        "detected_attributes": {
            logical: header_map[_normalize_header(alias)]
            for logical, aliases in AD_HEADER_ALIASES.items()
            for alias in aliases
            if _normalize_header(alias) in header_map
        },
        "risk_definitions": AD_RISK_DEFINITIONS,
        "risk_counts": risk_counts,
        "accounts": risky_accounts[:500],
    }

@app.route('/')
def dashboard():
    settings = data_manager.get_settings()
    timeframe = int(settings.get('timeframe', 6))
    upcoming_reminders = data_manager.get_upcoming_reminders(weeks=timeframe)
    future_reminders = data_manager.get_upcoming_reminders(weeks=12)
    all_tasks = data_manager.get_all_tasks()
    active_tasks = data_manager.get_active_tasks()
    all_projects = data_manager.get_all_projects()
    projects = [p for p in all_projects if p.get('status') != 'Completed']
    all_reminders = data_manager.get_all_reminders()
    user_name = data_manager.get_user_name()
    settings = data_manager.get_settings()
    counts = {
        'tasks_active': len(active_tasks),
        'tasks_done': len([t for t in all_tasks if t.get('status') == 'Completed']),
        'projects_active': len(projects),
        'projects_done': len([p for p in all_projects if p.get('status') == 'Completed']),
        'reminders_upcoming': len(upcoming_reminders),
        'reminders_total': len(all_reminders),
    }
    return render_template('dashboard.html',
                           upcoming_reminders=upcoming_reminders,
                           future_reminders=future_reminders,
                           active_tasks=active_tasks,
                           projects=projects,
                           user_name=user_name,
                           settings=settings,
                           counts=counts,
                           now=datetime.now())

@app.route('/all')
def all_items():
    reminders = data_manager.get_all_reminders()
    tasks = data_manager.get_all_tasks()
    kb_items = data_manager.get_kb_items()
    projects = data_manager.get_all_projects()
    return render_template('list_view.html', reminders=reminders, tasks=tasks, kb_items=kb_items, projects=projects)

@app.route('/calendar')
def calendar_view():
    today = datetime.now().date()
    start_date = today.replace(month=1, day=1) - timedelta(days=365)
    end_date = today.replace(month=12, day=31) + timedelta(days=365)
    projected = data_manager.get_projected_reminders(start_date, end_date)
    return render_template('calendar.html', reminders=projected)

@app.route('/knowledge')
def knowledge_base():
    return render_template('knowledge_base.html')

@app.route('/api/all_data')
def get_all_data():
    return jsonify({
        "reminders": data_manager.get_all_reminders(),
        "tasks": data_manager.get_all_tasks()
    })

# --- API Routes ---

@app.route('/api/reminders', methods=['POST'])
def add_reminder():
    data = request.json
    reminder = data_manager.add_reminder(
        data['title'], 
        data['description'], 
        data['date'], 
        data['recurrence'],
        data.get('start_time'),
        data.get('end_time')
    )
    return jsonify(reminder)

@app.route('/api/reminders/<reminder_id>', methods=['PUT'])
def update_reminder(reminder_id):
    data = request.json
    reminder = data_manager.update_reminder(
        reminder_id,
        data['title'],
        data['description'],
        data['date'],
        data['recurrence'],
        data.get('start_time'),
        data.get('end_time')
    )
    return jsonify(reminder)

@app.route('/api/tasks', methods=['POST'])
def add_task():
    data = request.json
    task = data_manager.add_task(
        data['title'], 
        data['description'], 
        data.get('status', 'Yet to Start')
    )
    return jsonify(task)

@app.route('/api/tasks/<task_id>', methods=['PUT'])
def update_task(task_id):
    data = request.json
    task = data_manager.update_task(
        task_id,
        data['title'],
        data['description'],
        data['status']
    )
    return jsonify(task)

@app.route('/api/comments', methods=['POST'])
def add_comment():
    data = request.json
    comment = data_manager.add_comment(
        data['item_type'], 
        data['item_id'], 
        data['text']
    )
    return jsonify(comment)

@app.route('/api/tasks/<task_id>/status', methods=['PUT'])
def update_task_status(task_id):
    data = request.json
    success = data_manager.update_task_status(task_id, data['status'])
    return jsonify({"success": success})

@app.route('/api/reminders/<reminder_id>', methods=['DELETE'])
def delete_reminder(reminder_id):
    data_manager.delete_reminder(reminder_id)
    return jsonify({"success": True})

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    data_manager.delete_task(task_id)
    return jsonify({"success": True})

# --- Bulk Upload API ---

@app.route('/api/csv-template')
def get_csv_template():
    import io
    import csv
    from flask import Response
    
    output = io.StringIO()
    writer = csv.writer(output)
    # Header: type, title, description, date/status, recurrence, start_time, end_time
    writer.writerow(['type', 'title', 'description', 'date_or_status', 'recurrence', 'start_time', 'end_time'])
    writer.writerow(['reminder', 'Buy Groceries', 'Milk, Bread, Eggs', '2026-01-20', 'Weekly', '10:00', '11:00'])
    writer.writerow(['task', 'Finish Report', 'Quarterly financial report', 'Yet to Start', '', '', ''])
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=bulk_upload_template.csv"}
    )

@app.route('/api/bulk-upload', methods=['POST'])
def bulk_upload():
    import io
    import csv
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and file.filename.endswith('.csv'):
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        reader = csv.DictReader(stream)
        
        imported_count = 0
        errors = []
        
        for row in reader:
            item_type = row.get('type', '').lower().strip()
            title = row.get('title', '').strip()
            description = row.get('description', '').strip()
            
            if not title:
                continue
                
            try:
                if item_type == 'reminder':
                    data_manager.add_reminder(
                        title,
                        description,
                        row.get('date_or_status', datetime.now().strftime('%Y-%m-%d')),
                        row.get('recurrence', 'None'),
                        row.get('start_time'),
                        row.get('end_time')
                    )
                    imported_count += 1
                elif item_type == 'task':
                    data_manager.add_task(
                        title,
                        description,
                        row.get('date_or_status', 'Yet to Start')
                    )
                    imported_count += 1
                else:
                    errors.append(f"Unknown type '{item_type}' for item '{title}'")
            except Exception as e:
                errors.append(f"Error importing '{title}': {str(e)}")
        
        return jsonify({
            "success": True, 
            "count": imported_count, 
            "errors": errors
        })
    
    return jsonify({"error": "Invalid file type"}), 400

# --- Knowledge Base API ---
@app.route('/api/kb', methods=['GET'])
def get_kb_items():
    return jsonify(data_manager.get_kb_items())

@app.route('/api/kb/search', methods=['GET'])
def search_kb_items():
    query = request.args.get('q', '')
    return jsonify(data_manager.search_kb_items(query))

@app.route('/api/kb', methods=['POST'])
def add_kb_item():
    data = request.json
    item = data_manager.add_kb_item(data['title'], data['data'], data['url'])
    return jsonify(item)

@app.route('/api/kb/<kb_id>', methods=['PUT'])
def update_kb_item(kb_id):
    data = request.json
    item = data_manager.update_kb_item(kb_id, data['title'], data['data'], data['url'])
    return jsonify(item)

@app.route('/api/kb/<kb_id>', methods=['DELETE'])
def delete_kb_item(kb_id):
    success = data_manager.delete_kb_item(kb_id)
    return jsonify({"success": success})

# --- Secure Vault API ---

@app.route('/secure')
def secure_view():
    vault_initialized = data_manager.is_secure_vault_initialized()
    return render_template('secure.html', vault_initialized=vault_initialized)

@app.route('/api/secure/init', methods=['POST'])
def init_secure_vault():
    data = request.json
    master_key = data.get('master_key')
    if not master_key:
        return jsonify({"success": False, "error": "Master Key required"}), 400
    
    success = data_manager.init_secure_vault(master_key)
    if success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Vault already exists"}), 400

@app.route('/api/secure/validate', methods=['POST'])
def validate_master_key():
    data = request.json
    master_key = data.get('master_key')
    f = data_manager.validate_master_key(master_key)
    return jsonify({"valid": f is not None})

@app.route('/api/secure/items', methods=['POST'])
def get_secure_items():
    data = request.json
    master_key = data.get('master_key')
    try:
        items = data_manager.get_secure_items(master_key)
        return jsonify(items)
    except ValueError:
        return jsonify({"error": "Invalid Master Key"}), 401

@app.route('/api/secure/add', methods=['POST'])
def add_secure_item():
    data = request.json
    master_key = data.get('master_key')
    item_data = data.get('item')
    try:
        item = data_manager.add_secure_item(master_key, item_data)
        return jsonify(item)
    except ValueError:
        return jsonify({"error": "Invalid Master Key"}), 401

@app.route('/api/secure/<item_id>', methods=['PUT'])
def update_secure_item(item_id):
    data = request.json
    master_key = data.get('master_key')
    item_data = data.get('item')
    try:
        item = data_manager.update_secure_item(master_key, item_id, item_data)
        return jsonify(item)
    except ValueError:
        return jsonify({"error": "Invalid Master Key"}), 401

@app.route('/api/secure/<item_id>', methods=['DELETE']) # Note: DELETE normally doesn't have body, but many clients support it. Safer to use POST for operations needing complex auth if headers aren't used. But we can put master_key in headers or query params? Plan said body. Flask supports body in DELETE.
def delete_secure_item(item_id):
    data = request.json
    master_key = data.get('master_key')
    try:
        success = data_manager.delete_secure_item(master_key, item_id)
        return jsonify({"success": success})
    except ValueError:
        return jsonify({"error": "Invalid Master Key"}), 401

@app.route('/settings')
def settings():
    return render_template('settings.html', user_name=data_manager.get_user_name())

@app.route('/small-apps')
def small_apps():
    return render_template('small_apps.html')

@app.route('/small-apps/otp')
def otp_generator():
    return render_template('otp_generator.html')

@app.route('/api/otp/generate', methods=['POST'])
def generate_otp():
    import pyotp
    data = request.json
    key = data.get('key')
    if not key:
        return jsonify({"error": "Key required"}), 400
    try:
        totp = pyotp.TOTP(key)
        return jsonify({"otp": totp.now(), "remaining": 30 - (int(time.time()) % 30)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/small-apps/dns')
def dns_resolver():
    return render_template('dns_resolver.html')

@app.route('/api/dns/resolve', methods=['POST'])
def resolve_dns():
    import dns.resolver
    data = request.json
    target = data.get('target')
    dns_server = data.get('dns_server')
    record_type = data.get('record_type', 'A')

    if not target:
        return jsonify({"error": "Target (DNS/IP) required"}), 400

    resolver = dns.resolver.Resolver()
    if dns_server:
        resolver.nameservers = [dns_server]

    types_to_query = [record_type]
    if record_type == 'ALL':
        types_to_query = ['A', 'AAAA', 'MX', 'TXT', 'CNAME', 'NS', 'SOA']

    results = []
    for rtype in types_to_query:
        try:
            answers = resolver.resolve(target, rtype)
            for rdata in answers:
                results.append({
                    "type": rtype,
                    "value": str(rdata)
                })
        except Exception as e:
            if record_type != 'ALL':
                return jsonify({"error": str(e)}), 400
            # For 'ALL', we just skip types that don't exist
            continue

    return jsonify({"results": results})

@app.route('/api/dns/trace', methods=['POST'])
def trace_dns():
    import dns.name
    import dns.query
    import dns.message
    import dns.resolver
    import dns.rdatatype

    data = request.json
    target_name = data.get('target')
    record_type = data.get('record_type', 'A')

    if not target_name:
        return jsonify({"error": "Target required"}), 400

    try:
        target = dns.name.from_text(target_name)
        rdtype = dns.rdatatype.from_text(record_type)
    except Exception as e:
        return jsonify({"error": f"Invalid input: {str(e)}"}), 400

    # Root servers
    roots = [
        '198.41.0.4', '199.9.14.201', '192.33.4.12', '199.7.91.13',
        '192.203.230.10', '192.5.5.241', '192.112.36.4', '198.97.190.53',
        '192.36.148.17', '192.58.128.30', '193.0.14.129', '199.7.83.42', '202.12.27.33'
    ]

    hops = []
    current_ns_list = roots
    depth = 0
    max_depth = 10 # Prevention of infinite loops

    while depth < max_depth:
        depth += 1
        ns_ip = current_ns_list[0] # Pick the first available
        hop = {
            "step": depth,
            "server": ns_ip,
            "query": target_name,
            "type": record_type,
            "status": "Querying...",
            "records": []
        }
        
        try:
            query = dns.message.make_query(target, rdtype)
            response = dns.query.udp(query, ns_ip, timeout=2.0)
            
            if response.answer:
                hop["status"] = "Authoritative Answer"
                for rrset in response.answer:
                    for rdata in rrset:
                        hop["records"].append(str(rdata))
                hops.append(hop)
                break # We found the answer
            
            if response.additional:
                # Look for glue records (A/AAAA) in additional section
                new_ns_list = []
                for rrset in response.additional:
                    if rrset.rdtype in [dns.rdatatype.A, dns.rdatatype.AAAA]:
                        for rdata in rrset:
                            new_ns_list.append(str(rdata))
                
                if new_ns_list:
                    hop["status"] = "Delegation (with Glue)"
                    for rrset in response.authority:
                         for rdata in rrset:
                             hop["records"].append(f"NS: {str(rdata)}")
                    hops.append(hop)
                    current_ns_list = new_ns_list
                    continue

            if response.authority:
                # No glue, need to resolve nameservers
                hop["status"] = "Delegation (No Glue)"
                ns_names = []
                for rrset in response.authority:
                    if rrset.rdtype == dns.rdatatype.NS:
                        for rdata in rrset:
                            ns_names.append(str(rdata))
                            hop["records"].append(f"NS: {str(rdata)}")
                
                hops.append(hop)
                
                if ns_names:
                    # Resolve one of the NS names using default resolver
                    try:
                        res = dns.resolver.resolve(ns_names[0], 'A')
                        current_ns_list = [str(r) for r in res]
                        continue
                    except:
                        break
                else:
                    break
            
            hop["status"] = "No Authority or Answer"
            hops.append(hop)
            break

        except Exception as e:
            hop["status"] = f"Error: {str(e)}"
            hops.append(hop)
            break

    return jsonify({"hops": hops})

@app.route('/small-apps/net-tools')
def net_tools():
    return render_template('net_tools.html')

@app.route('/small-apps/api-tester')
def api_tester():
    return render_template('api_tester.html')

@app.route('/small-apps/ad-risk-scanner')
def ad_risk_scanner():
    return render_template('ad_risk_scanner.html')

@app.route('/api/ad-risk/analyze', methods=['POST'])
def analyze_ad_risk():
    if 'file' not in request.files:
        return jsonify({"error": "No CSV file uploaded"}), 400

    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if not file.filename.lower().endswith('.csv'):
        return jsonify({"error": "Only CSV files are supported"}), 400

    try:
        inactive_days = int(request.form.get('inactive_days', 90))
        stale_password_days = int(request.form.get('stale_password_days', 180))
        inactive_days = min(max(inactive_days, 1), 3650)
        stale_password_days = min(max(stale_password_days, 1), 3650)
    except ValueError:
        return jsonify({"error": "Threshold values must be numbers"}), 400

    raw = file.stream.read()
    if len(raw) > 12 * 1024 * 1024:
        return jsonify({"error": "CSV file is too large. Please upload a file under 12 MB."}), 400

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    try:
        sample = text[:4096]
        dialect = csv.Sniffer().sniff(sample) if sample.strip() else csv.excel
    except csv.Error:
        dialect = csv.excel

    stream = io.StringIO(text, newline=None)
    reader = csv.DictReader(stream, dialect=dialect)
    if not reader.fieldnames:
        return jsonify({"error": "CSV must include a header row"}), 400

    rows = [row for row in reader if any((value or "").strip() for value in row.values())]
    if not rows:
        return jsonify({"error": "CSV did not contain any account rows"}), 400

    result = _analyze_ad_rows(rows, reader.fieldnames, inactive_days, stale_password_days)
    return jsonify(result)

@app.route('/api/net/check', methods=['POST'])
def check_connectivity():
    import socket
    data = request.json
    ips_input = data.get('ips', '')
    ports_input = data.get('ports', '')
    proto = data.get('protocol', 'TCP').upper()
    timeout_val = float(data.get('timeout', 2.0))
    
    if not ips_input:
        return jsonify({"error": "No IP addresses provided"}), 400
    if not ports_input:
        return jsonify({"error": "No ports provided"}), 400
    
    # Parse IPs (comma or newline separated)
    ips = [t.strip() for t in ips_input.replace('\n', ',').split(',') if t.strip()]
    
    # Parse Ports
    ports = []
    for p in ports_input.split(','):
        p = p.strip()
        if not p: continue
        if '-' in p:
            try:
                start, end = map(int, p.split('-'))
                ports.extend(range(start, end + 1))
            except:
                pass # Ignore bad ranges
        else:
            try:
                ports.append(int(p))
            except:
                pass # Ignore non-ints

    if not ports:
         # Default ports if parsing failed but input existed? 
         # Or strictly error? Let's default if empty list resulted from bad parse, 
         # but plan said "Both should accept multiple...". 
         # If user typed garbage, ports is empty.
         return jsonify({"error": "Invalid ports provided"}), 400

    results = []
    
    for host in ips:
        host_results = []
        for port in ports:
            status = "Success"
            error_msg = None
            
            try:
                if proto == 'TCP':
                    with socket.create_connection((host, port), timeout=timeout_val):
                        pass
                else:
                    # UDP Check
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.settimeout(timeout_val)
                    try:
                        sock.connect((host, port))
                        sock.send(b'')
                        # Try to read response? valid UDP services might not reply to empty packet.
                        # But we are keeping existing logic roughly, just updated timeout.
                        # If we want to be "modern", we might just trust Connect for UDP effectively means "route exists" 
                        # but rarely "port open" without app response.
                        # However, for this task, sticking to basic reachability check.
                        sock.recv(1024)
                    except ConnectionRefusedError:
                        raise Exception("Port is closed (ICMP Unreachable)")
                    except socket.timeout:
                        status = "Open|Filtered" 
                    except Exception as e:
                         # Some other socket error
                         raise e
                    finally:
                        sock.close()
            except Exception as e:
                status = "Failed"
                error_msg = str(e)
            
            host_results.append({
                "port": port,
                "status": status,
                "error": error_msg
            })
        
        results.append({
            "host": host,
            "protocol": proto,
            "results": host_results
        })
            
    return jsonify({"results": results})

@app.route('/api/net/cert', methods=['POST'])
def get_cert_details():
    import ssl
    import socket
    from OpenSSL import crypto
    from urllib.parse import urlparse
    
    data = request.json
    target = data.get('target', '').strip()
    if not target:
        return jsonify({"error": "Target required"}), 400
    
    # improved input parsing
    host = target
    port = 443
    
    # Attempt to handle http/https prefixes
    if target.lower().startswith(('http://', 'https://')):
        parsed = urlparse(target)
        host = parsed.hostname
        if parsed.port:
            port = parsed.port
        else:
            port = 443 if parsed.scheme == 'https' else 80
    elif ':' in target:
        # Handle host:port or ip:port
        parts = target.split(':')
        # If it's just host:port
        if len(parts) == 2:
            host = parts[0]
            try:
                port = int(parts[1])
            except:
                pass # invalid port, default 443
    
    try:
        # Fetch certificate
        if port in [587, 25]:
            import smtplib
            # Create unverified context to ensure we get cert even if invalid
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            server = smtplib.SMTP(host, port, timeout=10)
            server.ehlo()
            server.starttls(context=ctx)
            
            # Get binary cert (DER/ASN1)
            cert_der = server.sock.getpeercert(binary_form=True)
            cert = crypto.load_certificate(crypto.FILETYPE_ASN1, cert_der)
            server.quit()
        else:
            # Standard SSL/TLS connection
            cert_pem = ssl.get_server_certificate((host, port))
            cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_pem)
        
        subject = cert.get_subject()
        issuer = cert.get_issuer()
        
        # Helper to format ASN1 time
        def format_asn1_date(asn1_bytes):
            if not asn1_bytes: return "N/A"
            try:
                s = asn1_bytes.decode()
                # Format is usually YYYYMMDDHHMMSSZ
                dt = datetime.strptime(s, "%Y%m%d%H%M%SZ")
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                return str(asn1_bytes)

        # Extract SANs
        sans = []
        for i in range(cert.get_extension_count()):
            ext = cert.get_extension(i)
            if 'subjectAltName' in str(ext.get_short_name()):
                # str(ext) returns something like "DNS:example.com, DNS:www.example.com"
                sans = [x.strip().replace('DNS:', '') for x in str(ext).split(',')]
        
        details = {
            "subject": {k.decode(): v.decode() for k, v in subject.get_components()},
            "issuer": {k.decode(): v.decode() for k, v in issuer.get_components()},
            "version": cert.get_version(),
            "serial_number": cert.get_serial_number(),
            "notBefore": format_asn1_date(cert.get_notBefore()),
            "notAfter": format_asn1_date(cert.get_notAfter()),
            "expired": cert.has_expired(),
            "signature_algorithm": cert.get_signature_algorithm().decode(),
            "sans": sans
        }
        return jsonify(details)
    except Exception as e:
        return jsonify({"error": f"Failed to fetch cert from {host}:{port} - {str(e)}"}), 400

@app.route('/api/net/diagnostics', methods=['POST'])
def run_diagnostics():
    import subprocess
    data = request.json
    target = data.get('target', '').strip()
    tool = data.get('tool', 'ping').lower()
    
    if not target:
        return jsonify({"error": "Target required"}), 400
        
    try:
        if tool == 'ping':
            cmd = ['ping', '-c', '4', target]
        elif tool == 'tracert':
            cmd = ['traceroute', target]
        else:
            return jsonify({"error": "Invalid tool"}), 400
            
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return jsonify({
            "output": process.stdout,
            "error": process.stderr,
            "code": process.returncode
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/settings/username', methods=['GET', 'POST'])
def handle_username():
    if request.method == 'POST':
        data = request.json
        new_name = data.get('name')
        if new_name:
            data_manager.set_user_name(new_name)
            return jsonify({"success": True, "name": new_name})
        return jsonify({"success": False, "error": "Name required"}), 400
    else:
        return jsonify({"name": data_manager.get_user_name()})

@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    if request.method == 'POST':
        data = request.json
        data_manager.save_settings(data)
        return jsonify({"success": True})
    else:
        return jsonify(data_manager.get_settings())

@app.route('/api/backup', methods=['POST'])
def backup_data():
    try:
        # Use absolute path relative to this file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        backup_dir = os.path.join(base_dir, 'backup')
        
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Files identified from data_manager.py
        files_to_check = ['data.json', 'knowledgebase.json', 'secure.json', 'username.json']
        backed_up_files = []
        
        for filename in files_to_check:
            src = os.path.join(base_dir, filename)
            if os.path.exists(src):
                dst = os.path.join(backup_dir, f"{filename.split('.')[0]}_{timestamp}.json")
                shutil.copy2(src, dst)
                backed_up_files.append(os.path.basename(dst))
        
        if not backed_up_files:
            return jsonify({"success": False, "error": "No data files found to backup"}), 404
            
        return jsonify({"success": True, "path": backup_dir, "files": backed_up_files})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# --- Projects API ---
@app.route('/project/<project_id>')
def project_detail(project_id):
    project = data_manager.get_project(project_id)
    if not project:
        return redirect(url_for('dashboard'))
    return render_template('project.html', project=project)

@app.route('/api/projects', methods=['GET'])
def get_projects():
    return jsonify(data_manager.get_all_projects())

@app.route('/api/projects', methods=['POST'])
def add_project():
    data = request.json
    project = data_manager.add_project(
        data['name'],
        data['description'],
        data['start_date'],
        data['end_date'],
        data['status']
    )
    return jsonify(project)

@app.route('/api/projects/<project_id>', methods=['GET'])
def get_project(project_id):
    project = data_manager.get_project(project_id)
    if project:
        return jsonify(project)
    return jsonify({"error": "Project not found"}), 404

@app.route('/api/projects/<project_id>', methods=['PUT'])
def update_project(project_id):
    data = request.json
    result = data_manager.update_project(
        project_id,
        data['name'],
        data['description'],
        data['start_date'],
        data['end_date'],
        data['status']
    )
    if result:
        if isinstance(result, dict) and 'error' in result:
            return jsonify(result), 400
        return jsonify(result)
    return jsonify({"error": "Project not found"}), 404

@app.route('/api/projects/<project_id>', methods=['DELETE'])
def delete_project(project_id):
    success = data_manager.delete_project(project_id)
    return jsonify({"success": success})

@app.route('/api/projects/<project_id>/tasks', methods=['POST'])
def add_project_task(project_id):
    data = request.json
    task = data_manager.add_project_task(
        project_id,
        data['name'],
        data.get('comments', ''),
        data['start_date'],
        data['end_date'],
        data.get('parent_id')
    )
    if task:
        if "error" in task:
            return jsonify(task), 400
        return jsonify(task)
    return jsonify({"error": "Project not found"}), 404

@app.route('/api/projects/<project_id>/tasks/<task_id>', methods=['PUT'])
def update_project_task(project_id, task_id):
    data = request.json
    result = data_manager.update_project_task(
        project_id,
        task_id,
        data.get('name'),
        data.get('comments'),
        data.get('start_date'),
        data.get('end_date'),
        data.get('status')
    )
    if result:
        if isinstance(result, dict) and 'error' in result:
            return jsonify(result), 400
        return jsonify(result)
    return jsonify({"error": "Task not found"}), 404

@app.route('/api/projects/<project_id>/tasks/<task_id>', methods=['DELETE'])
def delete_project_task(project_id, task_id):
    success = data_manager.delete_project_task(project_id, task_id)
    return jsonify({"success": success})

@app.route('/api/projects/<project_id>/tasks/<task_id>/comments', methods=['POST'])
def add_project_task_comment(project_id, task_id):
    data = request.json
    comment = data_manager.add_project_task_comment(project_id, task_id, data['text'])
    if comment:
        return jsonify(comment)
    return jsonify({"error": "Task not found"}), 404

@app.route('/api/projects/<project_id>/tasks/<task_id>/status', methods=['PUT'])
def update_project_task_status(project_id, task_id):
    data = request.json
    success = data_manager.update_project_task_status(project_id, task_id, data['status'])
    return jsonify({"success": success})

@app.route('/api/projects/<project_id>/tasks/<task_id>/parent-dates', methods=['GET'])
def get_parent_task_dates(project_id, task_id):
    start_date, end_date = data_manager.get_parent_task_dates(project_id, task_id)
    if start_date and end_date:
        return jsonify({"start_date": start_date, "end_date": end_date})
    return jsonify({"error": "Parent task or dates not found"}), 404

@app.route('/api/reminders/download')
def download_reminders():
    import io
    import csv
    from flask import Response
    
    reminders = data_manager.get_all_reminders()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['id', 'title', 'description', 'date', 'recurrence', 'start_time', 'end_time', 'created_at'])
    
    for rem in reminders:
        writer.writerow([
            rem.get('id'),
            rem.get('title'),
            rem.get('description'),
            rem.get('date'),
            rem.get('recurrence'),
            rem.get('start_time', ''),
            rem.get('end_time', ''),
            rem.get('created_at')
        ])
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=reminders_export.csv"}
    )

@app.route('/api/tasks/download')
def download_tasks():
    import io
    import csv
    from flask import Response
    
    tasks = data_manager.get_all_tasks()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['id', 'title', 'description', 'status', 'created_at'])
    
    for task in tasks:
        writer.writerow([
            task.get('id'),
            task.get('title'),
            task.get('description'),
            task.get('status'),
            task.get('created_at')
        ])
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=tasks_export.csv"}
    )

@app.route('/api/projects/download')
def download_projects():
    import io
    import csv
    from flask import Response
    
    projects = data_manager.get_all_projects()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['id', 'name', 'description', 'start_date', 'end_date', 'status', 'created_at'])
    
    for project in projects:
        writer.writerow([
            project.get('id'),
            project.get('name'),
            project.get('description'),
            project.get('start_date'),
            project.get('end_date'),
            project.get('status'),
            project.get('created_at')
        ])
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=projects_export.csv"}
    )

@app.route('/api/check_update')
def check_update():
    try:
        # Get local modification time of app.py
        local_time = os.path.getmtime('app.py')
        local_date_obj = datetime.fromtimestamp(local_time)
        local_date = local_date_obj.strftime('%Y-%m-%d %H:%M:%S')
        
        # Get latest commit from GitHub
        url = "https://api.github.com/repos/BinuAppu/appupersonalapp/commits?per_page=1"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        commit_date_str = data[0]['commit']['committer']['date']
        # ISO 8601 format: 2023-10-27T10:00:00Z
        commit_date = datetime.strptime(commit_date_str, "%Y-%m-%dT%H:%M:%SZ")
        # Add timezone info to make it offset-aware (UTC) for fair comparison if we wanted, 
        # but for now just string comparison or simple boolean logic
        
        remote_date = commit_date.strftime('%Y-%m-%d %H:%M:%S')
        
        # Logic: If remote date > local date (with some buffer?), update available.
        # But local file time might be anything. A better way is checking a version file. 
        # Since we don't have one, we'll assume update available if remote seems "newer" in a general sense,
        # or just always true as requested to 'fix' it (user said 'not working as expected').
        # Actually user said "Check update is not working as expected, try to fix it."
        # The previous code hardcoded "update_available": True. Maybe that was the annoyance?
        # Let's try to be smart. If committer date is definitely after local mtime.
        
        # Converting local mtime to approximate UTC for comparison isn't perfect but better than nothing.
        # Let's just return the dates and let the frontend confirm, OR do the check here.
        
        # For this fix, let's just properly return the data and let's assume if the remote sha is different
        # from some stored version it's an update. We don't have stored version.
        # So we will rely on timestamps.
        
        update_available = False
        # Be generous, if remote is more than 24 hours ahead of local mod time, say update.
        # Or just show the dates.
        # The user's specific complaint "not working as expected" might mean it ALWAYS says update available.
        # Let's try to compare properly.
        # Local time is system time. 
        
        # Simplest fix: Just return the data and let the user see.
        # 'update_available' flag logic:
        # We will assume update provided if the remote commit date is strictly after local file mod time.
        # But local file mod time updates when we save this file! So after this edit, local time will be NOW.
        # Remote time might be OLDER. So it will say "Up to date". That is correct behavior.
        
        is_newer = commit_date > (local_date_obj - timedelta(minutes=5)) # buffer
        # Wait, if I just edited this file, local_date is NOW. commit_date is OLD (e.g. yesterday).
        # So commit_date < local_date. is_newer is False. Update available = False. Correct.
        
        return jsonify({
            "update_available": is_newer,
            "local_date": local_date,
            "remote_date": remote_date,
            "message": "Update available!" if is_newer else "You are up to date."
        })
    except Exception as e:
        return jsonify({"error": str(e), "update_available": False}), 500

if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=8000)
