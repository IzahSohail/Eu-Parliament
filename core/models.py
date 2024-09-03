from django.db import models

class MEP(models.Model):
    mep_id = models.IntegerField(primary_key=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    full_name = models.CharField(max_length=100, null=True)
    gender = models.CharField(max_length=6, null=True)
    date_of_birth = models.DateField(null=True)
    date_of_death = models.DateField(null=True)
    hometown = models.CharField(max_length=58, null=True)
    country_of_representation = models.CharField(max_length=3, null=True)
    photo = models.BinaryField(null=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class VoteInfo(models.Model):
    vote_id = models.CharField(primary_key=True, max_length=250)
    code = models.CharField(max_length=20, null=True)
    interinstitutional_file_no = models.CharField(max_length= 15, null=True)
    label = models.TextField(default="N/A", null=True)
    date = models.DateField()
    caller = models.CharField(max_length=109, null=True)
    rapporteur = models.CharField(max_length=255, null=True)
    committee_responsible = models.CharField(max_length=119, null=True)
    main_policy_issue = models.CharField(max_length=48, null=True)

    def __str__(self):
        return self.label

class VoteMapping(models.Model):
    vote = models.ForeignKey(VoteInfo, on_delete=models.CASCADE)
    mep = models.ForeignKey(MEP, on_delete=models.CASCADE)
    vote_type = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.mep} - {self.vote}"

class PoliticalGroup(models.Model):
    group = models.CharField(primary_key=True, max_length=89)

    def __str__(self):
        return self.group


class Membership(models.Model):
    mep = models.ForeignKey(MEP, on_delete=models.CASCADE)
    group = models.ForeignKey(PoliticalGroup, on_delete=models.CASCADE)
    start_date = models.DateField(null=True)
    end_date   = models.DateField(null=True)

    def __str__(self):
        return f"{self.mep} - {self.group}"