public with sharing class CaseHandoffAction {
 public class Request { @InvocableVariable(required=true) public Id caseId; @InvocableVariable(required=true) public Datetime expectedModified; @InvocableVariable(required=true) public String obligation; @InvocableVariable(required=true) public Date dueDate; }
 public class Result { @InvocableVariable public String state; @InvocableVariable public Id taskId; }
 @InvocableMethod(label='Create My Case Handoff Obligation' description='Creates Task owned by authenticated caller. Human acceptance/reassignment remains explicit.')
 public static List<Result> createTasks(List<Request> requests) {
  Set<Id> ids=new Set<Id>(); for(Request r:requests) if(r!=null && r.caseId!=null) ids.add(r.caseId);
  Map<Id,Case> rows=new Map<Id,Case>([SELECT Id,LastModifiedDate,IsClosed FROM Case WHERE Id IN :ids WITH USER_MODE]);
  List<Task> tasks=new List<Task>(); List<Integer> positions=new List<Integer>(); List<Result> out=new List<Result>(); Set<Id> seen=new Set<Id>();
  for(Request r:requests) {Result v=new Result(); v.state='HOLD'; Integer pos=out.size(); out.add(v); Case c=r==null?null:rows.get(r.caseId);
   if(c!=null && !c.IsClosed && r.expectedModified!=null && r.expectedModified==c.LastModifiedDate && !String.isBlank(r.obligation) && r.obligation.length()<=255 && r.dueDate!=null && r.dueDate>=Date.today() && !seen.contains(c.Id)) {
    seen.add(c.Id); tasks.add(new Task(WhatId=c.Id,OwnerId=UserInfo.getUserId(),Subject=r.obligation,ActivityDate=r.dueDate,Description='Case source modification: '+String.valueOf(c.LastModifiedDate)+'; obligation recorded by current user.')); positions.add(pos);
   }
  }
  if(!tasks.isEmpty()) {Database.SaveResult[] saved=Database.insert(tasks,false,AccessLevel.USER_MODE); for(Integer i=0;i<saved.size();i++) { Result v=out[positions[i]]; if(saved[i].isSuccess()) {v.state='OBLIGATION_CREATED'; v.taskId=saved[i].getId();} else v.state='WRITE_DENIED_OR_INVALID'; }} return out;
 }
}
