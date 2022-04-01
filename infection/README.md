# Infection

Module used for April Fools Day 2022.

You set a patient zero, which will be the first infected with a virus.
Anyone who gets in contact with them (sends a message directly after them) has a small chance of getting the virus as well.
No symptoms are visible from the start, there is a delay of three hours before the symptoms show up.
Twelve hours after the infection the member is healed.

---

**infection config init &lt;role&gt;**

Initiate the module.
Role ID is the role that will be assigned to symptomatic users -- the permissions are up to you.

**infection infect &lt;member&gt;**

Start the infection.
You can specify multiple patient zeros, it's really up to you.
Bots can be only infected by this command, they cannot catch it from the members.

**infection config ...**

Manage infection settings.
The management is fairly limited, the code was created in a day.

**infection check**

Command available to all members.

If they are not infected or are in asymptomatic phase, they will receive an information saying that they don't have any symptoms.
If they are infected, generic message about keeping others safe will be returned.

When the member is healthy again, this command returns information about their illness: the infectee, the timestamp and link to the message that caused them to get infected.

**infection graph**

Show graph of infections.
The graph is not very good, but it can provide you with some insights on how the infection spreads.

**infection list**

List all members with their illness status.
